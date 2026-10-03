"""Conservative Ren'Py dialogue reader and bounded RPA 2/3 extraction."""
import ast
import io
import pickle
import re
import zlib
from collections import Counter
from pathlib import Path, PurePosixPath

MAX_EXPANDED = 512 * 1024 * 1024
QUOTE = r'"(?:\\.|[^"\\])*"'
SAY = re.compile(r'^(?P<indent>\s*)(?:(?P<speaker>[A-Za-z_]\w*|'+QUOTE+r')(?P<attrs>(?:\s+[A-Za-z_]\w*)*)\s+)?(?P<text>'+QUOTE+r')(?P<tail>\s*(?::|(?:with\s+.*)?)(?:\s*#.*)?)$')
TOKENS = re.compile(r'\[\[|\[[^\[\]\n]+\]|\{\{|\{[^{}\n]+\}|\\[nrt]')
STATEMENTS = {'define', 'default', 'image', 'scene', 'show', 'hide', 'play', 'queue',
              'stop', 'voice', 'call', 'jump', 'return', 'pause', 'window', 'label',
              'menu', 'if', 'elif', 'else', 'while', 'for', 'init', 'python',
              'screen', 'style', 'transform', 'translate', 'old', 'new', 'with'}


def decode(text):
    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return text[1:-1]


def parse_script(source, filename):
    rows, names, warnings = [], {}, []
    scene, offset, blocked = 'Mở đầu', 0, None
    menu_indent = None
    for number, line in enumerate(source.splitlines(keepends=True), 1):
        body = line.rstrip('\r\n')
        indent = len(body) - len(body.lstrip())
        stripped = body.strip()
        definition = re.match(r'\s*define\s+(\w+)\s*=\s*Character\(\s*('+QUOTE+r')', body)
        if definition:
            names[definition[1]] = decode(definition[2])
        if blocked is not None and stripped and not stripped.startswith('#') and indent <= blocked:
            blocked = None
        if re.match(r'(?:init\b.*:|(?:\w+\s+)?python\b.*:|screen\b.*:|style\b.*:)', stripped):
            blocked = indent
        label = re.match(r'label\s+([^(:\s]+)', stripped)
        if label:
            scene = label[1]
        if menu_indent is not None and stripped and indent <= menu_indent and not stripped.startswith('menu'):
            menu_indent = None
        if stripped.startswith('menu') and stripped.endswith(':'):
            menu_indent = indent
        match = SAY.match(body) if blocked is None else None
        if match and match['speaker'] in STATEMENTS:
            match = None
        if match:
            is_choice = match['tail'].lstrip().startswith(':')
            if is_choice and menu_indent is None:
                match = None
            if match:
                raw = match['text']
                rows.append(dict(id=f'{filename}:{number}', file=filename, line=number,
                    scene=scene, speaker=(decode(match['speaker']) if match['speaker'].startswith('"') else match['speaker']) if match['speaker'] else 'Lời dẫn',
                    listener='', kind='Lựa chọn' if is_choice else 'Hội thoại',
                    text=decode(raw), translation='', start=offset+match.start('text'),
                    end=offset+match.end('text'), raw=raw))
        elif blocked is None and ('"""' in stripped or re.match(r'^"', stripped)):
            warnings.append(f'{filename}:{number}: Cú pháp chuỗi chưa hỗ trợ; cần kiểm tra thủ công.')
        offset += len(line)
    return rows, names, warnings


def validate_translation(original, translated):
    if not isinstance(translated, str) or not translated.strip():
        raise ValueError('Bản dịch phải là chuỗi có nội dung.')
    if Counter(TOKENS.findall(original)) != Counter(TOKENS.findall(translated)):
        raise ValueError('Bản dịch làm thay đổi biến hoặc thẻ định dạng Ren’Py.')
    if re.findall(r'\{[^{}\n]+\}', original) != re.findall(r'\{[^{}\n]+\}', translated):
        raise ValueError('Bản dịch làm thay đổi thứ tự thẻ Ren’Py.')


def quote_translation(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t') + '"'


def render_script(source, rows):
    for row in sorted(rows, key=lambda r: r['start'], reverse=True):
        if row['translation']:
            validate_translation(row['text'], row['translation'])
            source = source[:row['start']] + quote_translation(row['translation']) + source[row['end']:]
    return source


class DataUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        # Python 3 protocol-2 bytes use this reduce function. Accept only the
        # exact data conversion, never arbitrary codec lookups or classes.
        if module == '_codecs' and name == 'encode':
            return latin1_bytes
        if module in {'__builtin__', 'builtins'} and name == 'bytes':
            return empty_bytes
        raise ValueError('RPA chứa đối tượng không được phép.')


def latin1_bytes(value, encoding='latin1', errors='strict'):
    if not isinstance(value, str) or encoding not in {'latin1', 'latin-1'} or errors != 'strict':
        raise ValueError('Mã hóa dữ liệu RPA không hợp lệ.')
    return value.encode('latin1')


def empty_bytes():
    return b''


def extract_rpa(path, target):
    size = path.stat().st_size
    with path.open('rb') as f:
        header = f.readline(100).decode('ascii').strip().split()
        if header[0] not in {'RPA-2.0', 'RPA-3.0'}:
            raise ValueError('Chỉ hỗ trợ RPA-2.0 và RPA-3.0 thông thường.')
        index_offset = int(header[1], 16)
        key = int(header[2], 16) if header[0] == 'RPA-3.0' else 0
        if not 0 < index_offset < size:
            raise ValueError('Chỉ mục RPA không hợp lệ.')
        f.seek(index_offset)
        dec = zlib.decompressobj()
        blob = dec.decompress(f.read(), 32 * 1024 * 1024 + 1)
        if len(blob) > 32 * 1024 * 1024 or not dec.eof:
            raise ValueError('Chỉ mục RPA vượt giới hạn hoặc bị hỏng.')
        index = DataUnpickler(io.BytesIO(blob), encoding='bytes').load()
        if not isinstance(index, dict) or len(index) > 20000:
            raise ValueError('Chỉ mục RPA không hợp lệ.')
        total, paths = 0, []
        for name, chunks in index.items():
            name = name.decode('utf-8') if isinstance(name, bytes) else name
            rel = PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name or not name or '\x00' in name:
                raise ValueError('Đường dẫn trong RPA không an toàn.')
            dest = target.joinpath(*rel.parts)
            if dest.exists():
                raise ValueError(f'Tệp trùng: {name}')
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('wb') as out:
                for chunk in chunks:
                    offset, length = chunk[0] ^ key, chunk[1] ^ key
                    prefix = chunk[2] if len(chunk) > 2 else b''
                    if isinstance(prefix, str):
                        prefix = prefix.encode('latin1')
                    total += length
                    if total > MAX_EXPANDED or length < len(prefix) or offset < 0 or offset + length-len(prefix) > index_offset:
                        raise ValueError('Dữ liệu RPA vượt giới hạn hoặc bị hỏng.')
                    f.seek(offset)
                    data = f.read(length-len(prefix))
                    out.write(prefix + data)
            paths.append(dest)
    return paths

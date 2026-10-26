"""Compile validated human translations into normal glyphs plus numeric icons."""
import re
from text_tokens import TOKENS,validate

class DualEncoder:
    def __init__(self,normal,icons):
        self.normal=set(normal);self.icons=dict(icons);self.reverse={v:k for k,v in self.icons.items()}
        if self.normal & set(self.icons):raise ValueError('Glyph assigned to both fonts')
        if len(self.reverse)!=len(self.icons) or any(not 38<=n<=65535 for n in self.reverse):raise ValueError('Invalid supplemental IDs')
    def encode(self,text):
        # Protect original tokens as indivisible units. Only plain glyphs are
        # mapped; the human CSV never contains generated icon markup.
        out=[];at=0
        for match in TOKENS.finditer(text):
            out.append(self._plain(text[at:match.start()]));token=match.group()
            if token.startswith('[b=') and token[3:-1].isdigit() and int(token[3:-1]) in self.reverse:raise ValueError('Original token collides with generated ID')
            out.append(token);at=match.end()
        out.append(self._plain(text[at:]));encoded=''.join(out)
        if self.decode(encoded)!=text:raise ValueError('Character mapping round-trip failed')
        return encoded
    def _plain(self,text):
        out=[]
        for char in text:
            cp=ord(char)
            if cp in self.normal:out.append(char)
            elif cp in self.icons:out.append(f'[b={self.icons[cp]}]')
            else:raise ValueError(f'Missing glyph U+{cp:04X}')
        return ''.join(out)
    def decode(self,text):
        def replace(m):
            code=int(m[1]);return chr(self.reverse[code]) if code in self.reverse else m[0]
        return re.sub(r'\[b=(\d+)\]',replace,text)
    def validate_row(self,row):
        validate(row['source'],row['translation']);encoded=self.encode(row['translation']);validate(row['source'],self.decode(encoded));return encoded

"""Version-pinned modal-state adapter; no installed package/source edits.

Ucamco Gerber 2024.05 §8.3, p193: deprecated D01 state persists until
another D code; G01/G02/G03/G74/G75 do not clear it. D02/D03/aperture
selection leave subsequent omitted-operation coordinates undefined.
"""
import hashlib,importlib.metadata
from pathlib import Path
from gerbonara import GerberFile,rs274x

SOURCE_SHA='88d906d6be3fda501b5d526f73e4c39df905b4ebffcaeacc7a63c51b2a12a2bb'
SPEC='https://www.ucamco.com/files/downloads/file_en/456/gerber-layer-format-specification-revision-2024-05_en.pdf'

class ModalStateParser(rs274x.GerberParser):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.state_adaptations=[]
    def _parse_coord(self,match):
        parts=match.groups();interp,*_,op=parts
        has_coord=any(parts[i] for i in (2,4,6,8));previous=self.last_operation
        value=super()._parse_coord(match)
        if interp in ('G01','G02','G03','G74','G75') and not has_coord and op is None:
            if self.last_operation!=previous:
                self.state_adaptations.append(dict(line=self.lineno,command=self.line,previous=previous,base_parser_result=self.last_operation,qualified_result=previous))
            self.last_operation=previous
        return value
    def _parse_aperture(self,match):
        value=super()._parse_aperture(match)
        if self.last_operation is not None:
            self.state_adaptations.append(dict(line=self.lineno,command=self.line,previous=self.last_operation,base_parser_result=self.last_operation,qualified_result=None))
        self.last_operation=None
        return value

def parse_legacy(data,filename=None):
    assert importlib.metadata.version('gerbonara')=='1.6.3'
    with Path(rs274x.__file__).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==SOURCE_SHA,'Parser changed; requalify adapter'
    target=GerberFile();parser=ModalStateParser(target,include_dir=None)
    parser.parse(data,filename=filename)
    return target,dict(status='PINNED_MODAL_STATE_COMPATIBILITY_ADAPTER',spec=SPEC,section='8.3 Coordinate Data without Operation Code, page 193',base_parser_sha256=SOURCE_SHA,state_adaptations=parser.state_adaptations)

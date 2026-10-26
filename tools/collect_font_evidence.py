"""Collect small private FONT resources; never uploads anything."""
import hashlib,json,struct,sys,zipfile
from pathlib import Path
from viv import index
from str_stream import unpack_selected
SOURCE_SHA='8e6035b2c03a12bb7492209776cd877176849cc2aa3362d29130e310326e0d4c'

def collect(source,output):
    h=hashlib.sha256()
    with source.open('rb') as f:
        while block:=f.read(8*1024*1024):h.update(block)
    if h.hexdigest()!=SOURCE_SHA:raise ValueError('请使用原版 VIV，不能选择 F1 或其他补丁版。')
    if output.exists():raise ValueError('输出 ZIP 已存在，请改名保留。')
    entries=index(source)['entries'];assets={};report={'source_sha256':h.hexdigest(),'resources':[]}
    paths={f'shared\\fonts\\{face}.{ext}' for face in ('buttons','minion_pro') for ext in ('inf','tg4h','tg4d')}
    with source.open('rb') as f:
        for n in (298,2095):
            e=entries[n];f.seek(e['offset']);raw=f.read(e['size'])
            for path,data in unpack_selected(raw,paths).items():
                name=f'{n}/'+path.rsplit('\\',1)[-1];assets[name]=data
                item={'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
                if path.endswith('.inf'):
                    count=struct.unpack_from('>H',data,10)[0];start=struct.unpack_from('>I',data,12)[0]
                    if data[:4]!=b'FONT' or start+24*count>len(data):raise ValueError('字库结构不匹配')
                    item['glyphs']=count;item['codepoints']=[int.from_bytes(data[start+i*24:start+i*24+2],'little') for i in range(count)]
                report['resources'].append(item)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(assets.items()):z.writestr(name,data)
        z.writestr('font-evidence.json',json.dumps(report,ensure_ascii=False,indent=2))
    print('已保存：',output,'\n仅包含两套字库资源及校验报告，没有上传。请勿将其提交到公开仓库。')

if __name__=='__main__':
    if len(sys.argv)==1:
        import tkinter as tk
        from tkinter import filedialog,messagebox
        root=tk.Tk();root.withdraw()
        path=filedialog.askopenfilename(title='选择原版 bigfile0.viv',filetypes=[('VIV','*.viv')])
        if path:
            try:collect(Path(path),Path.cwd()/'Dante-Private-Font-Evidence.zip');messagebox.showinfo('完成','已生成 Dante-Private-Font-Evidence.zip，可提供给汉化分析。不要提交到公开仓库。')
            except Exception as e:messagebox.showerror('未完成',str(e))
    else:
        collect(Path(sys.argv[1]),Path(sys.argv[2]))

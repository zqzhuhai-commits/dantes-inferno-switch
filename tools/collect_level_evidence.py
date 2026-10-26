"""Read-only collection of pinned original level stream and related tables.
Private analysis material; never uploads or modifies the source game.
"""
import hashlib,json,sys,zipfile
from pathlib import Path
from viv import index
TARGETS={
298:(1569507328,26869760,'25c2710d','20971f33f1d08e743fc839a207633b8016a29164b5fe5a99d0226835535caa0d'),
2:(1569323008,26624,'00253a68','19f2501c33ebe3e316cf26048b65e57f3e00be0a702ec68ca59a0491c15cd4fb'),
302:(1596377088,26624,'263b7f44','19f2501c33ebe3e316cf26048b65e57f3e00be0a702ec68ca59a0491c15cd4fb'),
1096:(1569480704,26624,'81ba42d2','19f2501c33ebe3e316cf26048b65e57f3e00be0a702ec68ca59a0491c15cd4fb'),
752:(1682780160,131072,'59999774','23dc9401f49c2f01ef5e9a42d34ff89f9278238cbe485a14199f9475cf7935a1'),
1437:(1366546432,131072,'a9b47ccc','23dc9401f49c2f01ef5e9a42d34ff89f9278238cbe485a14199f9475cf7935a1'),
}

def collect(source,output):
    source,output=Path(source),Path(output)
    if source.stat().st_size!=3170839904:raise ValueError('原包大小不匹配，请选择原版 bigfile0.viv。')
    entries=index(source)['entries'];assets={};report={'source_size':source.stat().st_size,'validation':'selected original entry hashes; not a whole-file hash','entries':[]}
    if output.exists():raise ValueError('输出文件已存在，请先另存保留。')
    with source.open('rb') as f:
        for n,(offset,size,key,digest) in TARGETS.items():
            e=entries[n]
            if (e['offset'],e['size'],e['key'])!=(offset,size,key):raise ValueError('原包索引不匹配：'+str(n))
            f.seek(offset);data=f.read(size)
            if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('资源不是原版：'+str(n)+'。请恢复原版后采集，不能选 F3/G2。')
            assets[str(n)+'.bin']=data;report['entries'].append(dict(index=n,offset=offset,size=size,key=key,sha256=digest))
    # Exclusive output creation; all validation occurs before creating the ZIP.
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
        for name,data in assets.items():z.writestr(name,data)
        z.writestr('level-evidence.json',json.dumps(report,ensure_ascii=False,indent=2))
    return output

if __name__=='__main__':
    if len(sys.argv)==1:
        import tkinter as tk
        from tkinter import filedialog,messagebox
        root=tk.Tk();root.withdraw()
        name=filedialog.askopenfilename(title='选择原版 bigfile0.viv（只读采集）',filetypes=[('VIV','*.viv')])
        if name:
            try:
                out=collect(name,Path.cwd()/'Dante-Private-Level-Evidence.zip')
                messagebox.showinfo('采集完成',str(out)+'\n游戏文件未修改。请在对话中提供这个 ZIP；不要上传公开仓库。')
            except Exception as e:messagebox.showerror('采集未完成',str(e))
    else:
        if len(sys.argv)!=3:raise SystemExit('Usage: collect_level_evidence.py original.viv output.zip')
        print(collect(sys.argv[1],sys.argv[2]))

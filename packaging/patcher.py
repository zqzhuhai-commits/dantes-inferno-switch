"""Dante Chinese test patch installer. Standard-library only; preserves original."""
from pathlib import Path
import csv
import hashlib
import json
import os
import shutil
import struct
import sys
import threading
import queue
from datetime import datetime

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'tools'))
from viv import index
from lh2_build import rebuild
from lh2 import parse
from str_stream import reflow,unpack_selected


def sha_file(path,notify=lambda *a:None,cancel=lambda:False):
    h=hashlib.sha256();total=Path(path).stat().st_size;done=0
    with Path(path).open('rb') as f:
        while True:
            if cancel():raise ValueError('已取消。原文件未修改。')
            data=f.read(8*1024*1024)
            if not data:break
            h.update(data);done+=len(data);notify('校验文件',done,total)
    return h.hexdigest()


def make_resources(source,manifest):
    entries=index(source)['entries'];payloads={};old={}
    with Path(source).open('rb') as f:
        for target in manifest['targets']:
            i=target['index']
            if i>=len(entries):raise ValueError('VIV 条目数不匹配')
            item=entries[i]
            if any(item[k]!=target[k] for k in ['key','size','offset']):raise ValueError('VIV 索引版本不匹配')
            f.seek(item['offset']);data=f.read(item['size'])
            if hashlib.sha256(data).hexdigest()!=target['sha256']:raise ValueError('原始资源版本不匹配：'+item['key'])
            old[i]=data
    translations=[]
    for name in manifest['translation_files']:
        with (BASE/name).open(encoding='utf-8-sig',newline='') as f:translations.extend(csv.DictReader(f))
    font_paths=['minion_pro.inf','minion_pro.tg4d','minion_pro.tg4h']
    fonts={f'shared\\fonts\\{name}':(BASE/'font'/name).read_bytes() for name in font_paths}
    deltas={}
    for target in manifest['targets']:
        i=target['index'];data=old[i]
        if target['kind']=='text':
            payloads[i]=rebuild(data,translations)
            deltas['text']=struct.unpack_from('>I',payloads[i],0x90)[0]-struct.unpack_from('>I',data,0x90)[0]
        elif target['kind']=='font':
            payloads[i],delta=reflow(data,fonts)
            if unpack_selected(payloads[i],fonts)!=fonts:raise ValueError('新字库资源重读校验失败')
            deltas[target['decoded_size']]=delta
    for target in manifest['targets']:
        if target['kind']!='toc':continue
        i=target['index'];data=bytearray(old[i])
        if data[:4]!=bytes.fromhex('9cba7b28'):raise ValueError('TOC 标识不匹配')
        count=struct.unpack_from('>H',data,8)[0]
        if 16+count*20>len(data):raise ValueError('TOC 目录越界')
        found_text=found_font=False
        for row in range(count):
            at=16+20*row;ptr,size=struct.unpack_from('>II',data,at)
            if ptr+8>len(data):raise ValueError('TOC 引用越界')
            key=struct.unpack_from('>I',data,ptr)[0]
            if key==0 and row==0:
                if size not in deltas:raise ValueError('TOC 字体流内存长度不匹配')
                struct.pack_into('>I',data,at+4,size+deltas[size]);found_font=True
            elif key==0xe00af020:
                if size!=116272:raise ValueError('TOC 英文表长度不匹配')
                struct.pack_into('>I',data,at+4,size+deltas['text']);found_text=True
        if not found_text or not found_font:raise ValueError('缺少 TOC 字体/英文文本引用')
        payloads[i]=bytes(data)
    return entries,payloads


def apply(source,output,install=False,notify=lambda *a:None,cancel=lambda:False):
    source,output=Path(source),Path(output)
    manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
    if source.resolve()==output.resolve():raise ValueError('输出路径不能与原文件相同')
    partial=Path(str(output)+'.partial')
    if output.exists() or partial.exists():raise ValueError('输出或 .partial 文件已存在，请换一个输出名称')
    if source.stat().st_size!=manifest['source_size']:raise ValueError('原包大小不匹配，未修改文件')
    if sha_file(source,notify,cancel)!=manifest['source_sha256']:raise ValueError('原包 SHA-256 不匹配，未修改文件')
    for name,checksum in manifest['package_sha256'].items():
        if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=checksum:raise ValueError('补丁文件校验失败：'+name)
    notify('重建文本与字库',0,1);entries,payloads=make_resources(source,manifest)
    expected_size=manifest['output_size']
    if shutil.disk_usage(output.parent).free < expected_size+64*1024*1024:
        raise ValueError('剩余空间不足，至少需要容纳一整份修改后的 VIV')
    owned=False
    try:
        with source.open('rb') as original,partial.open('xb') as patched:
            owned=True;done=0;copy_hash=hashlib.sha256()
            while True:
                if cancel():raise ValueError('已取消。原文件未修改。')
                block=original.read(8*1024*1024)
                if not block:break
                patched.write(block);copy_hash.update(block);done+=len(block);notify('复制原始 VIV',done,manifest['source_size'])
            if copy_hash.hexdigest()!=manifest['source_sha256']:raise ValueError('复制期间原包内容发生变化')
            for number in sorted(payloads):
                if cancel():raise ValueError('已取消。原文件未修改。')
                offset=patched.seek(0,2);padding=(-offset)%2048
                patched.write(bytes(padding));offset+=padding
                payload=payloads[number];stored=(len(payload)+2047)&~2047
                patched.write(payload);patched.write(bytes(stored-len(payload)))
                patched.seek(16+12*number);patched.write(struct.pack('>II',offset,stored))
            final_size=patched.seek(0,2)
            if final_size!=expected_size or final_size>0xffffffff:raise ValueError('输出长度不匹配或超过 BIGH 限制')
            patched.seek(4);patched.write(struct.pack('<I',final_size))
            patched.flush();os.fsync(patched.fileno())
        if sha_file(partial,notify,cancel)!=manifest['output_sha256']:
            raise ValueError('生成文件 SHA-256 不匹配，已停止安装')
        # Verify every new resource and all index ranges before publishing.
        verified=index(partial)['entries']
        with partial.open('rb') as f:
            for number,payload in payloads.items():
                e=verified[number];f.seek(e['offset'])
                if e['key']!=entries[number]['key'] or f.read(len(payload))!=payload:
                    raise ValueError('输出资源字节校验失败')
        if cancel():raise ValueError('已取消。原文件未修改。')
        # Hard-link publication refuses existing paths without replacing them.
        # Use rename on Windows (which also refuses an existing destination).
        if os.name=='nt':partial.rename(output)
        else:os.link(partial,output);partial.unlink()
        owned=False
        backup=None
        if install:
            if source.parent.resolve()!=output.parent.resolve():raise ValueError('自动安装需要原文件与输出文件位于同一目录。已保留生成文件。')
            stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            backup=source.with_name(source.name+'.original.'+stamp+'.bak')
            if backup.exists():raise ValueError('备份名称冲突。已保留生成文件。')
            source.rename(backup)
            try:output.rename(source)
            except BaseException:
                backup.rename(source)
                raise
        return source if install else output,backup
    finally:
        if owned:partial.unlink(missing_ok=True)


def gui():
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    root=tk.Tk();root.title('但丁的地狱 Switch 简体中文测试补丁 v0.1');root.geometry('800x580')
    root.columnconfigure(0,weight=1)
    source=tk.StringVar();output=tk.StringVar();automatic=tk.BooleanVar(value=True);status=tk.StringVar(value='请选择上传游戏包对应的原版 bigfile0.viv')
    stop=threading.Event();events=queue.Queue();busy=False
    ttk.Label(root,text='但丁的地狱 · 简体中文实机测试补丁 v0.1',font=('',15,'bold')).grid(row=0,column=0,padx=20,pady=15,sticky='w')
    ttk.Label(root,text='156 条菜单/教程初稿 + 421 个新增字形 | 游戏内显示待验证').grid(row=1,column=0,padx=20,sticky='w')
    form=ttk.Frame(root);form.grid(row=2,column=0,padx=20,pady=15,sticky='ew');form.columnconfigure(0,weight=1)
    def choose():
        p=filedialog.askopenfilename(filetypes=[('VIV 资源包','*.viv')])
        if p:source.set(p);output.set(str(Path(p).with_name('bigfile0_zh_test_v01.viv')))
    ttk.Label(form,text='原始 VIV').grid(row=0,column=0,sticky='w');ttk.Entry(form,textvariable=source).grid(row=1,column=0,sticky='ew')
    ttk.Button(form,text='选择…',command=choose).grid(row=1,column=1,padx=8)
    ttk.Label(form,text='输出文件（需与原文件同目录）').grid(row=2,column=0,pady=(12,0),sticky='w');ttk.Entry(form,textvariable=output).grid(row=3,column=0,columnspan=2,sticky='ew')
    ttk.Checkbutton(root,text='生成并校验成功后自动备份安装；原版保留为 .original.日期.bak',variable=automatic).grid(row=3,column=0,padx=20,sticky='w')
    progress=ttk.Progressbar(root,maximum=100);progress.grid(row=4,column=0,padx=20,pady=15,sticky='ew')
    ttk.Label(root,textvariable=status,wraplength=750).grid(row=5,column=0,padx=20,sticky='w')
    def notify(stage,done,total):events.put(('progress',stage,done,total))
    def start():
        nonlocal busy
        if busy:return
        if not source.get() or not output.get():messagebox.showerror('选择文件','请先选择原始 VIV');return
        src,dst,install=source.get(),output.get(),automatic.get()
        if install and Path(src).parent.resolve()!=Path(dst).parent.resolve():messagebox.showerror('路径检查','自动安装请使用同一目录');return
        busy=True;stop.clear();button.configure(state='disabled')
        def worker():
            try:events.put(('done',apply(src,dst,install,notify,stop.is_set)))
            except Exception as e:events.put(('error',str(e)))
        threading.Thread(target=worker,daemon=True).start()
    buttons=ttk.Frame(root);buttons.grid(row=6,column=0,padx=20,pady=12,sticky='w')
    button=ttk.Button(buttons,text='开始制作并安装',command=start);button.pack(side='left')
    ttk.Button(buttons,text='取消',command=stop.set).pack(side='left',padx=12)
    helpbox=tk.Text(root,height=11,wrap='word');helpbox.grid(row=7,column=0,padx=20,pady=(0,15),sticky='nsew');root.rowconfigure(7,weight=1)
    helpbox.insert('1.0',(BASE/'README-TEST.txt').read_text(encoding='utf-8'));helpbox.configure(state='disabled')
    def pump():
        nonlocal busy
        while not events.empty():
            event=events.get()
            if event[0]=='progress':status.set(event[1]);progress['value']=100*event[2]/max(event[3],1)
            else:
                busy=False;button.configure(state='normal')
                if event[0]=='done':
                    path,backup=event[1];status.set('制作成功，待实机显示验证')
                    messagebox.showinfo('完成',f'当前文件：{path}\n原版备份：{backup or "未替换原文件"}\n请按说明进行实机测试。')
                else:status.set(event[1]);messagebox.showerror('操作未完成',event[1])
        root.after(100,pump)
    def close():
        if busy:stop.set();status.set('正在取消，请等处理结束后关闭。')
        else:root.destroy()
    root.protocol('WM_DELETE_WINDOW',close);pump();root.mainloop()


if __name__=='__main__':
    if len(sys.argv)==1:gui()
    else:
        import argparse
        p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');p.add_argument('--install',action='store_true');args=p.parse_args()
        result=apply(args.source,args.output,args.install,lambda stage,done,total:print(f'{stage}: {done}/{total}',flush=True))
        print('完成：',result)

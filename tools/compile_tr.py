from pathlib import Path
import importlib.util,json
root=Path(__file__).resolve().parents[1];out={}
for p in sorted((root/'work/tr').glob('ko_*.py')):
    spec=importlib.util.spec_from_file_location('translation',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    out.update(getattr(m,'T',{}))
(root/'work/tr/messages_ko.json').write_text(json.dumps(out,ensure_ascii=False,indent=1),encoding='utf-8')
print(len(out),'scenario messages')

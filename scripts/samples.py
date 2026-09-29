from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

def main():
    folder=Path('apps/web/public/samples');folder.mkdir(parents=True,exist_ok=True)
    (folder/'stock.csv').write_text('batch,quantity,unit,mode,observed_at\nA-MED-001,40,tablet,snapshot,2026-09-27T09:00:00+00:00\n')
    img=Image.new('RGB',(1000,650),'#faf9f1');d=ImageDraw.Draw(img)
    try: font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',32);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
    except OSError: font=ImageFont.load_default(size=32);small=ImageFont.load_default(size=24)
    lines=['SYNTHETIC SAMPLE - NOT A REAL PHARMACY RECORD','Fictional PHC A / State A / District D1','Stock card: 27 September 2026, 09:00 scenario time','','Product: Paracetamol 500 mg tablets','Catalogue: MED-001','Lot: SYN-01 / Expiry: 27 September 2027','Counted stock: 40 tablets','Pack: 10 tablets per pack / 4 packs total','','Human confirmation required before reconciliation.']
    for i,line in enumerate(lines): d.text((40,35+i*50),line,font=small if i in [0,10] else font,fill='#234b40')
    img.save(folder/'stock-card.png');print('Synthetic image and CSV written; no fabricated audio sample.')
if __name__=='__main__': main()

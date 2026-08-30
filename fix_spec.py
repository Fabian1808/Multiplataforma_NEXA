with open('nexa_hub.spec', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('`n', '\n')
with open('nexa_hub.spec', 'w', encoding='utf-8') as f:
    f.write(c)

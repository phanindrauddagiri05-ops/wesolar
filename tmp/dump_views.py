
with open(r'c:\Users\Phanindra\OneDrive\Desktop\Phani\wesolar\wesolar\solar_management\views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(985, 995):
        print(f"{i+1}: {repr(lines[i])}")

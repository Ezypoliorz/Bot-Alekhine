import pandas as pd

df = pd.DataFrame({'Nom': ['Alice', 'Bob'], 'Score': ["25", "30"], "Test":["AAAAAAAAAAAAAAAAAAA", "B"]})

players = 10

with pd.ExcelWriter("formatage.xlsx", engine="xlsxwriter") as writer:
    df.to_excel(writer, index=False, sheet_name="Sheet1", startrow=1, startcol=2)
    
    workbook  = writer.book
    worksheet = writer.sheets["Sheet1"]

    bold_bordure = workbook.add_format({
        'font_name': 'Arial',
        'font_size': 14,
        'font_color': '#3498db',
        'bold': True,
        'align': 'center',
        'border': 1
    })

    bordure = workbook.add_format({
        'font_name': 'Arial',
        'font_size': 14,
        'font_color': 'black',
        'align': 'center',
        'border': 1
    })

    worksheet.conditional_format("B2:E2", {"type": "no_errors", "format": bold_bordure})
    worksheet.conditional_format(f"B3:E{2+players}", {"type": "no_errors", "format": bordure})

    for i, col in enumerate(df.columns):
        max_len = max(
            df[col].astype(str).map(len).max(),
            len(str(col))
        )
        max_len += 2 + 20/100*max_len

        worksheet.set_column(i+2, i+2, max_len)

print("Fichier 'formatage.xlsx' créé avec succès.")
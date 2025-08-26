import pandas as pd



df = pd.read_csv("/Users/tarekradwan/Downloads/hr_database/extras2.csv")
df.replace("None", "", inplace=True)
df.to_csv("/Users/tarekradwan/Downloads/hr_database/extras2.csv", index=False)
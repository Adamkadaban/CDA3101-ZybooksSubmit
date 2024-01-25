#!/usr/bin/env python3

import pandas as pd

path = './thing.xlsx'
df = pd.read_excel(path)
print(df['Last name'])

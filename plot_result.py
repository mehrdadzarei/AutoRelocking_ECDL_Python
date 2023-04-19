


import pandas as pd
# from datetime import datetime
import matplotlib.pyplot as plt


df = pd.read_csv('data/relock_data_689.csv')

df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
df['freq'] *= 1e6
# print(df['time'])

plt.plot(df['time'], df['freq'])
# plt.show()
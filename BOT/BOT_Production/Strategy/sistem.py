import math
from binance.client import Client
from binance.helpers import round_step_size
# import keys
import time

import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import numpy as np
from finta import TA
from APIBinance.Config import Config

# получаем баланс
def get_av_balance(client, time):
    while True:
        try:
            account_info = client.futures_account()

            av_balance = None
            for asset in account_info["assets"]:
                if asset["asset"] == "USDT":
                    av_balance = float(asset["availableBalance"])

            if len(account_info) > 0:
                av_balance = float("{:.2f}".format(av_balance))
                return av_balance

        except Exception as e:
            print("Account Error:", e)
            time.sleep(1)
            pass

def create_sequences(df, look_back=1):
  x = []
  if look_back == len(df):
    x.append(MinMaxScaler(feature_range=(-1, 1)).fit_transform(df))
  else:
    print("Длина look_back и длина df не совпадают")
    return 0

  return np.array(x)

def predict(symbol, interval, client):


    # Загружаем модель
    model = tf.keras.models.load_model('Strategy/LSTM_Binance_1h_v6.6.3-4.h5')
    look_back = 24

    # Получаем последние 100 данных
    df = last_data(symbol, interval, "100", client)
    df_predict = df

    # Создание последовательностей для обучения и тестирования
    arr = model.predict(create_sequences(df_predict.iloc[-look_back:], look_back))

    return arr

# Получаем данные о цене
def last_data(symbol, interval, lookback, client):
    frame = pd.DataFrame(client.get_historical_klines(symbol, interval, lookback + 'hour ago UTC'))
    frame = frame.iloc[:,:6]
    frame.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    # извлекаем столбец 'Time'
    frame.pop('Time')
    frame = frame.astype(float)
    frame['SMA7'] = TA.SMA(frame, 7)
    frame['SMA12'] = TA.SMA(frame, 12)
    frame['SMA20'] = TA.SMA(frame, 20)
    frame['SMA25'] = TA.SMA(frame, 25)
    frame['SMA99'] = TA.SMA(frame, 99)
    frame['RSI'] = TA.RSI(frame)
    frame['OBV'] = TA.OBV(frame)
    frame.fillna(0, inplace=True)

    # извлекаем столбец 'close' из середины и сохраняем его в переменной
    close_col = frame.pop('Close')
    # добавляем столбец 'close' в конец
    frame.insert(len(frame.columns), 'Close', close_col)
    frame.head(len(frame.columns))

    return frame


# client = Client(Config.BINANCE_API_KEY, Config.BINANCE_API_SECRET)
# last_data("BTCUSDT", "1h", "24", client)

# Расчет размера позиции на покупку/продажу
def quantity_lot(balance, balanceProcent, price):
    quantity = 0
    # торгуем % баланса
    balance = balance * balanceProcent
    # расчет размера позиции на покупку/продажу
    quantity = balance / price
    quantity = math.floor(quantity * 1000) / 1000.0
    return quantity

def get_tick_size(symbol: str, client) -> float:
    info = client.futures_exchange_info()

    for symbol_info in info['symbols']:
        if symbol_info['symbol'] == symbol:
            for symbol_filter in symbol_info['filters']:
                if symbol_filter['filterType'] == 'PRICE_FILTER':
                    return float(symbol_filter['tickSize'])

def get_rounded_price(symbol: str, price: float, client) -> float:
    return round_step_size(price, get_tick_size(symbol, client))











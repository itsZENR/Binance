import time
import requests
import datetime
from binance.client import Client
from APIBinance.Config import Config
from Strategy.sistem import get_av_balance, predict, last_data, quantity_lot, get_rounded_price
from aiogram import Bot, Dispatcher, executor, types

# bot tg
api_token = '6103836646:AAHML_5KbEfqiEv_IILnbqQq-UGAAcS7gV8'
chat_id = '-922282584'

# Подключаемся к фьючерскому аккаунту
client = Client(api_key=Config.BINANCE_API_KEY, api_secret=Config.BINANCE_API_SECRET)


# Баланс
balance = get_av_balance(client, time)
# Торгуем % от баланса
balanceProcent = 100
# % Take-profit
procent_profit = 5.7
# % Stop-loss
stop_loss_procent = 4.5


balanceProcent = balanceProcent / 100
TP = procent_profit / 100
SL = stop_loss_procent / 100
open_positions = None




print(f'Свободный баланс: {balance}')
print(f'Take-profit: {procent_profit} %')
print(f'Stop-loss: {stop_loss_procent} %')
# Отправлять сообщения в группу
# requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
#     chat_id=chat_id,
#     text=f'Начальный баланс: {balance} \nTake-profit: {procent_profit} % \nStop-loss: {stop_loss_procent} %'
# ))


def main_strateg():

    while True:
        try:
            # Подключение к бинансу
            client = Client(Config.BINANCE_API_KEY, Config.BINANCE_API_SECRET)
            symbol = 'BTCUSDT'
            interval = '1h'

            # Проверка на наличие открытых позиций
            position_symbol = client.futures_position_information(symbol=symbol)[0]['symbol']
            position_volume = client.futures_position_information(symbol=symbol)[0]['positionAmt']
            position_price = client.futures_position_information(symbol=symbol)[0]['entryPrice']
            position_profit = client.futures_position_information(symbol=symbol)[0]['unRealizedProfit']

            # Размер позиции
            position_mark_price = client.futures_position_information(symbol=symbol)[0]['markPrice']
            position_entry_price = client.futures_position_information(symbol=symbol)[0]['entryPrice']
            position_size = abs(float(position_volume)) * float(position_entry_price)
            position_size_mark = abs(float(position_volume)) * float(position_mark_price)
            position_size_difference = position_size_mark - position_size

            # Информация о сегодняшней дате и времени
            data_time = datetime.datetime.today().weekday()
            data_minute = datetime.datetime.now()
            if data_time < 5 and data_minute.minute >= 55:
                # Баланс
                balance = get_av_balance(client, time)

                if float(position_volume) == 0:
                    # Обновить статус позиции
                    open_positions = None
                    # Заркрыть все лимитки
                    client.futures_cancel_all_open_orders(symbol=symbol, timestamp=1000)
                    # Отправлять сообщения в группу
                    requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                        chat_id=chat_id,
                        text=f'Текущих открытых позиций нет \nBalance: {balance} USDT'
                    ))
                elif float(position_volume) > 0:
                    # Обновить статус позиции
                    open_positions = "rise"
                    # Отправлять сообщения в группу
                    requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                        chat_id=chat_id,
                        text=f'Текущая позиция: {open_positions}  \nСимвол: {symbol} \nОбъем: {position_volume} \nПрибыль: {position_profit}'
                    ))
                    # Процент прибыли BUY
                    # position_procent_profit = (position_size_difference * 100) / position_size_mark
                    # Переводим стоп в БУ
                    # if round(position_procent_profit, 2) >= 0.5:
                    #     Отправлять сообщения в группу
                    #     requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                    #         chat_id=chat_id,
                    #         text=f'Перевожу стоп в БУ'
                    #     ))
                    #     # Stop-loss
                    #     order_sell_SL = client.futures_create_order(
                    #         symbol=symbol,
                    #         side="SELL",
                    #         type="STOP_MARKET",
                    #         quantity=position_volume,
                    #         stopPrice=price,
                    #         closePosition=True,
                    #         timeInForce="GTC"
                    #     )
                elif float(position_volume) < 0:
                    # Обновить статус позиции
                    open_positions = "fall"
                    position_volume = abs(float(position_volume))  # берем по модулю
                    # Отправлять сообщения в группу
                    requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                        chat_id=chat_id,
                        text=f'Текущая позиция: {open_positions}  \nСимвол: {symbol} \nОбъем: {position_volume} \nПрибыль: {position_profit}'
                    ))

                    # Процент прибыли SELL
                    # position_procent_profit = (-position_size_difference * 100) / position_size_mark
                    # Переводим стоп в БУ
                    # if round(position_procent_profit, 2) >= 0.5:
                        # Отправлять сообщения в группу
                        # requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                        #     chat_id=chat_id,
                        #     text=f'Перевожу стоп в БУ'
                        # ))
                        # Stop-loss
                        # order_sell_SL = client.futures_create_order(
                        #     symbol=symbol,
                        #     side="BUY",
                        #     type="STOP_MARKET",
                        #     quantity=position_volume,
                        #     stopPrice=price,
                        #     closePosition=True,
                        #     timeInForce="GTC"
                        # )

                # Предсказание
                try:
                    prediction = predict(symbol, interval, client)
                    print(f"Prediction: {prediction}")
                except Exception as e:
                    print(f"Prediction error: {e}")

                # Получаем данные о цене
                df = last_data(symbol, interval, "1", client)
                price = df.Close.iloc[-1]
                price = get_rounded_price(symbol, price, client)

                # Stop-loss
                stop_loss = int(price * SL)
                # Take profit
                take_profit = int(price * TP)
                # Направление predict
                price_movement = ""

                if prediction > 0:  # Если модель предсказывает рост
                    price_movement = "rise"
                elif prediction <= 0:  # Если модель предсказывает падение
                    price_movement = "fall"

                print("open_positions:", open_positions)
                print("price_movement:", price_movement)

                # проверяем условия для открытия или закрытия позиций
                if price_movement == "rise" and open_positions is None:  # если предсказан рост цены и нет открытых позиций, то открываем позицию на покупку
                    # расчет размера позиции на покупку/продажу
                    qty = quantity_lot(balance, balanceProcent, price)
                    print(
                        f'Заходим в покупку по цене {price}, объем: {qty}, SL: {price - stop_loss}, TP: {price + take_profit}')

                    # Отправлять сообщения в группу
                    requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                        chat_id=chat_id,
                        text=f'Заходим в покупку по цене {price} \nОбъем: {qty} \nSL: {price - stop_loss} \nTP: {price + take_profit}'
                    ))

                    # расчет размера позиции на покупку/продажу
                    qty = quantity_lot(balance, balanceProcent, price)

                    # Order Buy
                    order_buy = client.futures_create_order(
                        newCliendOrderID="Order_1",
                        symbol=symbol,
                        side="BUY",
                        type="LIMIT",
                        quantity=qty,
                        Price=price + 50,
                        timeInForce="GTC"
                    )

                    # Stop-loss
                    order_sell_SL = client.futures_create_order(
                        newCliendOrderID="Order_SL",
                        symbol=symbol,
                        side="SELL",
                        type="STOP_MARKET",
                        quantity=qty,
                        stopPrice=price - stop_loss,
                        closePosition=True,
                        timeInForce="GTC"
                    )

                    # Take-profit
                    order_sell_TP = client.futures_create_order(
                        newCliendOrderID="Order_TP",
                        symbol=symbol,
                        side="SELL",
                        type="TAKE_PROFIT_MARKET",
                        quantity=qty,
                        stopPrice=price + take_profit,
                        closePosition=True,
                        timeInForce="GTC"
                    )

                    open_positions = "rise"
                elif price_movement == "fall" and open_positions is None:  # если предсказано падение цены и нет открытых позиций, то открываем позицию на продажу

                    # расчет размера позиции на покупку/продажу
                    qty = quantity_lot(balance, balanceProcent, price)
                    print(
                        f'Заходим в продажу по цене {price}, объем: {qty}, SL: {price + stop_loss}, TP: {price - take_profit}')

                    # Отправлять сообщения в группу
                    requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                        chat_id=chat_id,
                        text=f'Заходим в продажу по цене {price} \nОбъем: {qty} \nSL: {price + stop_loss} \nTP: {price - take_profit}'
                    ))

                    # Order Sell
                    order_sell = client.futures_create_order(
                        newClientOrderId="Order_1",
                        symbol=symbol,
                        side="SELL",
                        type="LIMIT",
                        quantity=qty,
                        Price=price - 50,
                        timeInForce="GTC"
                    )

                    # Stop-loss
                    order_sell_SL = client.futures_create_order(
                        newClientOrderId="Order_SL",
                        symbol=symbol,
                        side="BUY",
                        type="STOP_MARKET",
                        quantity=qty,
                        stopPrice=price + stop_loss,
                        closePosition=True,
                        timeInForce="GTC"
                    )

                    # Take-profit
                    order_sell_TP = client.futures_create_order(
                        newClientOrderId="Order_TP",
                        symbol=symbol,
                        side="BUY",
                        type="TAKE_PROFIT_MARKET",
                        quantity=qty,
                        stopPrice=price - take_profit,
                        closePosition=True,
                        timeInForce="GTC"
                    )

                    # обновляем значение переменной для открытых позиций
                    open_positions = "fall"
                elif price_movement == "rise" and open_positions == "fall":  # если предсказан рост цены и есть открытая позиция на продажу, то закрываем ее
                    print(f'Закрываем ордер ')
                    position_volume = client.futures_position_information(symbol=symbol)[0]['positionAmt']
                    position_volume = abs(float(position_volume))  # берем по модулю
                    client.futures_cancel_all_open_orders(symbol=symbol, timestamp=5000)
                    # Close order sell
                    order_buy = client.futures_create_order(
                        symbol=symbol,
                        side="BUY",
                        type="MARKET",
                        quantity=position_volume,
                    )

                    print(
                        f'Balance: {balance} USDT, Заходим в покупку по цене {price}, объем{position_volume}, SL: {price - stop_loss}, TP: {price + take_profit}')

                    # Отправлять сообщения в группу
                    requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                        chat_id=chat_id,
                        text=f'Заходим в покупку по цене {price} \nОбъем{position_volume} \nSL: {price - stop_loss} \nTP: {price + take_profit}'
                    ))

                    # расчет размера позиции на покупку/продажу
                    qty = quantity_lot(balance, balanceProcent, price)

                    # Order Buy
                    order_buy = client.futures_create_order(
                        symbol=symbol,
                        side="BUY",
                        type="LIMIT",
                        quantity=qty,
                        Price=price + 50,
                        timeInForce="GTC"
                    )

                    # Stop-loss
                    order_sell_SL = client.futures_create_order(
                        symbol=symbol,
                        side="SELL",
                        type="STOP_MARKET",
                        quantity=qty,
                        stopPrice=price - stop_loss,
                        closePosition=True,
                        timeInForce="GTC"
                    )

                    # Take-profit
                    order_sell_TP = client.futures_create_order(
                        symbol=symbol,
                        side="SELL",
                        type="TAKE_PROFIT_MARKET",
                        quantity=qty,
                        stopPrice=price + take_profit,
                        closePosition=True,
                        timeInForce="GTC"
                    )

                    # обновляем значение переменной для открытых позиций
                    open_positions = "rise"
                elif price_movement == "fall" and open_positions == "rise":  # если предсказано падение цены и есть открытая позиция на покупку, то закрываем ее
                    print(f'Закрываем ордер')
                    position_volume = client.futures_position_information(symbol=symbol)[0]['positionAmt']
                    position_volume = abs(float(position_volume))  # берем по модулю
                    client.futures_cancel_all_open_orders(symbol=symbol, timestamp=5000)
                    # Close order buy
                    order_buy = client.futures_create_order(
                        symbol=symbol,
                        side="SELL",
                        type="MARKET",
                        quantity=position_volume,
                    )

                    print(
                        f'Заходим в продажу по цене {price}, объем{position_volume}, SL: {price + stop_loss}, TP: {price - take_profit}')

                    # Отправлять сообщения в группу
                    requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                        chat_id=chat_id,
                        text=f'Заходим в продажу по цене {price} \nОбъем{position_volume} \nSL: {price + stop_loss} \nTP: {price - take_profit}'
                    ))

                    # расчет размера позиции на покупку/продажу
                    qty = quantity_lot(balance, balanceProcent, price)

                    # Order Sell
                    order_sell = client.futures_create_order(
                        symbol=symbol,
                        side="SELL",
                        type="LIMIT",
                        quantity=qty,
                        Price=price - 50,
                        timeInForce="GTC"
                    )

                    # Stop-loss
                    order_sell_SL = client.futures_create_order(
                        symbol=symbol,
                        side="BUY",
                        type="STOP_MARKET",
                        quantity=qty,
                        stopPrice=price + stop_loss,
                        closePosition=True,
                        timeInForce="GTC"
                    )

                    # Take-profit
                    order_sell_TP = client.futures_create_order(
                        symbol=symbol,
                        side="BUY",
                        type="TAKE_PROFIT_MARKET",
                        quantity=qty,
                        stopPrice=price - take_profit,
                        closePosition=True,
                        timeInForce="GTC"
                    )

                    # обновляем значение переменной для открытых позиций
                    open_positions = "fall"
                else:
                    pass

                time.sleep(300)  # 5 min
            elif data_time < 5 and data_minute.minute < 55:
                print(f"{data_minute}, Ждём-с")
                time.sleep(300)  # 5 min
            else:
                print("Выходной")
                time.sleep(3600)
        except Exception as e:
            print(f"Error: {e}")
            # Отправлять сообщения в группу
            requests.get('https://api.telegram.org/bot{}/sendMessage'.format(api_token), params=dict(
                chat_id=chat_id,
                text=f'Error: {e}'
            ))
            time.sleep(300)  # 5 min

main_strateg()

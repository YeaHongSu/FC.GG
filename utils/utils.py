import numpy as np
import pandas as pd
import requests
import copy
from datetime import datetime, timedelta


def me(match, me):
    if match['matchInfo'][0]['nickname'].lower() == me.lower():
        return match['matchInfo'][0]
    else:
        return match['matchInfo'][1]

def you(match, me):
    if match['matchInfo'][1]['nickname'].lower() != me.lower():
        return match['matchInfo'][1]
    else:
        return match['matchInfo'][0]
    
def avg_data():
    url = f"https://fconline.nexon.com/Datacenter/GetMatchRecord?strDate={datetime.now().strftime('%Y.%m.%d')}&n1Type=50&n4StartRanking=1&n4EndRanking=10000&rd=0.4988530727702105"
    response = requests.get(url)
    json_obj = response.json()
    df = pd.DataFrame(json_obj)  # JSON 데이터를 DataFrame으로 변환
    return df.iloc[-1, :]

def top_n_argmax(array, n):
    top_n_indices = []
    top_n_values = []
    arr = copy.deepcopy(array)
    for _ in range(n):
        max_index = np.nanargmax(arr)
        top_n_indices.append(max_index)
        top_n_values.append(arr[max_index])
        arr[max_index] = -np.inf
    return top_n_indices, top_n_values

def top_n_argmin(array, n):
    top_n_indices = []
    top_n_values = []
    arr = copy.deepcopy(array)
    for _ in range(n):
        min_index = np.nanargmin(arr)
        top_n_indices.append(min_index)
        top_n_values.append(arr[min_index])
        arr[min_index] = np.inf
    return top_n_indices, top_n_values


def calculate_time_difference(date_str):
    current_time = datetime.now()
    input_time = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
    time_difference = current_time - input_time

    if time_difference < timedelta(days=1):
        hours_diff = int(time_difference.total_seconds() // 3600)
        minutes_diff = int((time_difference.total_seconds() % 3600) // 60)
        if hours_diff == 0:
            if minutes_diff <= 1:
                return "방금 전"
            else:
                return f"{minutes_diff}분 전"
        elif hours_diff == 1:
            return "1시간 전"
        else:
            return f"{hours_diff}시간 전"
    else:
        days_diff = time_difference.days
        if days_diff == 1:
            return "1일 전"
        else:
            return f"{days_diff}일 전"

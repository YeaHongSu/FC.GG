import numpy as np
import pandas as pd
import requests
import copy
from datetime import datetime, timedelta


# def me(match, me):
#     if match['matchInfo'][0]['nickname'].lower() == me.lower() or len(match['matchInfo'][:])==1:
#         return match['matchInfo'][0]
#     else:
#         return match['matchInfo'][1]

# def you(match, me):
#     if match['matchInfo'][0]['nickname'].lower() != me.lower() or len(match['matchInfo'][:])==1:
#         return match['matchInfo'][0]
#     else:
#         return match['matchInfo'][1]

def me(match, me):
    me = me.replace(" ", "")  # 입력받은 닉네임에서 띄어쓰기 제거
    if match['matchInfo'][0]['nickname'].replace(" ", "").lower() == me.lower() or len(match['matchInfo'][:]) == 1:
        return match['matchInfo'][0]
    else:
        return match['matchInfo'][1]

def you(match, me):
    me = me.replace(" ", "")  # 입력받은 닉네임에서 띄어쓰기 제거
    if match['matchInfo'][0]['nickname'].replace(" ", "").lower() != me.lower() or len(match['matchInfo'][:]) == 1:
        return match['matchInfo'][0]
    else:
        return match['matchInfo'][1]

    
# def avg_data():
#     url = f"https://fconline.nexon.com/Datacenter/GetMatchRecord?strDate={datetime.now().strftime('%Y.%m.%d')}&n1Type=50&n4StartRanking=1&n4EndRanking=10000&rd=0.4988530727702105"
#     response = requests.get(url)
#     json_obj = response.json()
#     df = pd.DataFrame(json_obj)  # JSON 데이터를 DataFrame으로 변환
#     return df.iloc[-1, :]

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


def avg_data(match_type):
    # 미리 저장된 JSON 데이터를 불러옴
    data_1 = {"lengthDate":30,"date":["2024-12-08T00:00:00","2024-12-09T00:00:00","2024-12-10T00:00:00","2024-12-11T00:00:00","2024-12-12T00:00:00","2024-12-13T00:00:00","2024-12-14T00:00:00","2024-12-15T00:00:00","2024-12-16T00:00:00","2024-12-17T00:00:00","2024-12-18T00:00:00","2024-12-19T00:00:00","2024-12-20T00:00:00","2024-12-21T00:00:00","2024-12-22T00:00:00","2024-12-23T00:00:00","2024-12-24T00:00:00","2024-12-25T00:00:00","2024-12-26T00:00:00","2024-12-27T00:00:00","2024-12-28T00:00:00","2024-12-29T00:00:00","2024-12-30T00:00:00","2024-12-31T00:00:00","2025-01-01T00:00:00","2025-01-02T00:00:00","2025-01-03T00:00:00","2025-01-04T00:00:00","2025-01-05T00:00:00","2025-01-06T00:00:00"],"count":[25654,20359,20443,21011,44429,41501,41955,39869,29901,29790,29882,25151,28636,32200,31700,25336,24144,26946,21756,22484,25955,29206,23445,23635,27163,21291,22748,28138,26316,20886],"avggoaltot":[2.57567,2.59296,2.57567,2.54783,2.66246,2.67918,2.66349,2.6475,2.6348,2.6129,2.6186,2.6323,2.619,2.6257,2.6376,2.6094,2.5802,2.6081,2.5974,2.6072,2.6303,2.6206,2.5904,2.5992,2.603,2.6182,2.6061,2.6264,2.6116,2.6248],"avgshoottot":[6.92901,6.90403,6.90044,6.81037,7.21891,7.17829,7.1422,7.1165,7.0389,6.9703,6.9638,6.9905,6.9932,6.9754,7.007,6.9448,6.8839,6.9124,6.8645,6.9209,6.9775,6.9737,6.9231,6.9411,6.9521,6.9629,6.9714,7.0226,7.0195,6.9735],"avgeffshoottot":[5.27497,5.25785,5.25437,5.17813,5.45834,5.43943,5.42407,5.4111,5.3479,5.3122,5.3067,5.3284,5.325,5.3228,5.3345,5.2927,5.2483,5.2674,5.2417,5.2816,5.3246,5.3249,5.2722,5.2864,5.2987,5.3126,5.3116,5.363,5.3562,5.3317],"avggoalpenaltykick":[0.06331,0.06384,0.06316,0.06331,0.06288,0.06327,0.06542,0.0636,0.0637,0.0634,0.0635,0.0641,0.065,0.0656,0.0645,0.0641,0.0636,0.064,0.0618,0.062,0.0626,0.0641,0.0624,0.0634,0.0615,0.0624,0.0633,0.0625,0.0616,0.0607],"avggoalfreekick":[0.01754,0.01847,0.01932,0.0175,0.0177,0.0171,0.01943,0.0187,0.0186,0.0189,0.019,0.0186,0.0171,0.0189,0.0186,0.0172,0.019,0.0191,0.018,0.0178,0.0186,0.0193,0.0173,0.0191,0.0176,0.0201,0.0181,0.019,0.0193,0.0167],"avgshootinpenalty":[4.63882,4.63728,4.61918,4.59343,4.85819,4.82392,4.79887,4.7869,4.7435,4.6913,4.6789,4.7279,4.7219,4.7029,4.7218,4.6817,4.6396,4.6458,4.6504,4.693,4.7066,4.6961,4.6588,4.6682,4.6698,4.6971,4.6739,4.7133,4.6862,4.7038],"avggoalinpenalty":[2.03811,2.0543,2.03535,2.03057,2.10179,2.11498,2.10375,2.0965,2.0854,2.0636,2.0697,2.091,2.0728,2.0808,2.0872,2.0633,2.0438,2.0596,2.0643,2.0802,2.0881,2.0745,2.0534,2.0643,2.0561,2.0768,2.0543,2.0711,2.0539,2.0844],"avgshootoutpenalty":[2.20006,2.17767,2.19366,2.12689,2.26964,2.26415,2.24996,2.2387,2.2057,2.1907,2.1968,2.1718,2.1806,2.1824,2.1933,2.1728,2.1563,2.1773,2.1281,2.142,2.1814,2.1873,2.1776,2.184,2.1961,2.1781,2.2084,2.2207,2.247,2.1836],"avggoaloutpenalty":[0.47425,0.47482,0.47716,0.45395,0.49779,0.50093,0.49431,0.4874,0.4857,0.4859,0.4854,0.4773,0.4812,0.4792,0.4858,0.482,0.4728,0.4845,0.4712,0.465,0.4796,0.482,0.4746,0.4715,0.4853,0.479,0.4885,0.4928,0.496,0.4797],"middleshoot":[21.5564,21.8041,21.7516,21.3435,21.9327,22.1243,21.9698,21.7726,22.0204,22.1804,22.0938,21.9775,22.066,21.9584,22.1503,22.1823,21.925,22.2508,22.143,21.7069,21.9862,22.0386,21.7954,21.5904,22.1008,21.9918,22.1192,22.1898,22.0758,21.9691],"outpenaltygoalratio":[18.4128,18.312,18.5255,17.8172,18.6967,18.6971,18.5588,18.4098,18.434,18.5962,18.5366,18.1324,18.3734,18.2504,18.4183,18.4717,18.3242,18.5767,18.1412,17.8352,18.2337,18.3927,18.3215,18.1402,18.6439,18.295,18.7445,18.7633,18.9922,18.2757],"avggoalheading":[0.26361,0.27838,0.27384,0.27463,0.27026,0.27594,0.27042,0.2777,0.2787,0.2769,0.2794,0.2826,0.2866,0.2816,0.2751,0.2864,0.28,0.2713,0.279,0.2799,0.2794,0.2844,0.2842,0.2721,0.2804,0.2804,0.2858,0.2789,0.2812,0.2847],"goalheadingratio":[10.2347,10.736,10.6318,10.7789,10.1507,10.2993,10.1528,10.491,10.5779,10.599,10.6697,10.7354,10.9423,10.7265,10.4312,10.9747,10.8513,10.4002,10.7402,10.7345,10.6228,10.8507,10.9695,10.4676,10.7704,10.7103,10.9658,10.6188,10.7662,10.8472],"avgpasstry":[105.488,105.636,106.022,105.658,102.559,102.936,103.538,103.896,104.207,104.163,104.144,103.405,103.834,103.659,104.671,104.867,105.096,104.748,104.676,104.764,104.828,104.661,104.974,104.41,105.068,105.114,105.174,105.852,106.17,105.362],"avgpasssuccess":[95.3241,95.5105,95.9796,95.6616,92.1457,92.6761,93.344,93.6974,94.0518,94.0867,94.1017,93.4205,93.7831,93.6161,94.5225,94.754,95.0445,94.7701,94.5611,94.6529,94.6662,94.6032,94.9408,94.3569,94.995,94.949,95.0089,95.6198,95.9613,95.1985],"passsuccessratio":[90.365,90.4149,90.528,90.5387,89.847,90.0326,90.1543,90.1839,90.2544,90.3261,90.3578,90.3448,90.3201,90.3112,90.3041,90.3564,90.4359,90.4746,90.3367,90.3483,90.3065,90.3905,90.4422,90.3715,90.4125,90.3296,90.3349,90.3334,90.3845,90.3541],"avgowngoal":[0.01749,0.01767,0.018,0.01884,0.01671,0.01593,0.01651,0.0178,0.0178,0.0178,0.0168,0.0179,0.0181,0.018,0.0177,0.0183,0.0168,0.0179,0.0178,0.0171,0.0179,0.0171,0.0175,0.0184,0.0183,0.017,0.0161,0.0182,0.0173,0.0184],"avgpossession":[50.5155,50.4501,50.5476,50.5408,50.755,50.8405,50.8248,50.7689,50.7188,50.705,50.6605,50.7708,50.7156,50.7335,50.6508,50.6592,50.682,50.6787,50.5696,50.5926,50.551,50.6633,50.6822,50.5864,50.56,50.5298,50.5121,50.4702,50.5163,50.5502],"avgdribble":[73.0965,73.1725,73.6462,73.4018,71.4535,71.5594,72.1252,72.2523,72.4996,72.5414,72.4842,72.1173,72.1494,72.2706,72.5426,72.7679,73.1208,73.1137,72.8043,72.8793,73.044,72.8275,72.971,72.5335,73.1069,73.1766,73.1528,73.2279,73.6012,73.1378],"avgtacklesuccess":[6.12276,6.08594,6.08092,6.07445,6.29903,6.244,6.19058,6.152,6.109,6.091,6.0659,6.1195,6.1301,6.1305,6.1175,6.0966,6.0863,6.0971,6.1125,6.1558,6.1378,6.1201,6.0494,6.1571,6.0826,6.1791,6.1383,6.1336,6.0721,6.0489],"avgtackletry":[11.4667,11.4165,11.4167,11.4173,11.6288,11.5797,11.4733,11.4445,11.3778,11.3491,11.3068,11.3539,11.4205,11.4421,11.4542,11.3896,11.3787,11.3567,11.4302,11.4945,11.4937,11.4526,11.3348,11.536,11.3868,11.5704,11.5098,11.49,11.3887,11.3748],"avgblocksuccess":[0.60955,0.61983,0.61421,0.60766,0.61372,0.61047,0.61076,0.6137,0.6086,0.6105,0.6101,0.6032,0.6056,0.608,0.6145,0.6075,0.6064,0.6132,0.5952,0.6119,0.6127,0.6137,0.616,0.609,0.6193,0.6136,0.6166,0.619,0.6218,0.6097],"avgblocktry":[8.25696,8.26357,8.24493,8.22356,8.11325,8.10724,8.13512,8.1759,8.1497,8.1262,8.141,8.0815,8.0919,8.116,8.1915,8.1707,8.1574,8.1642,8.1445,8.2103,8.2738,8.2356,8.1911,8.2105,8.2536,8.314,8.2934,8.3555,8.3491,8.2609],"avgfoul":[0.70601,0.71303,0.69918,0.70677,0.72274,0.70941,0.70844,0.7076,0.7057,0.7027,0.6964,0.7063,0.7044,0.7041,0.7141,0.6968,0.7014,0.7001,0.6996,0.7111,0.7004,0.7158,0.6981,0.7132,0.7056,0.7124,0.7184,0.7073,0.6936,0.697],"avgshootfreekick":[0.18704,0.18813,0.18461,0.18832,0.18015,0.18032,0.18247,0.1852,0.184,0.1801,0.1787,0.1866,0.1831,0.1807,0.1812,0.1814,0.185,0.1826,0.1811,0.1845,0.1821,0.1892,0.1826,0.1905,0.181,0.1884,0.1845,0.1826,0.1824,0.1797],"avgshootpenaltykick":[0.08217,0.08185,0.08036,0.08307,0.08256,0.08253,0.08484,0.0825,0.0818,0.0814,0.0808,0.083,0.0837,0.083,0.084,0.0822,0.0808,0.082,0.0789,0.0789,0.0812,0.083,0.0796,0.0818,0.0786,0.0796,0.0819,0.0809,0.0792,0.0787],"avgshootheading":[0.89543,0.92637,0.92264,0.91664,0.93974,0.9382,0.93485,0.9419,0.9419,0.9375,0.941,0.946,0.9502,0.9405,0.9322,0.958,0.9319,0.9163,0.9363,0.9262,0.937,0.9509,0.9411,0.9226,0.9357,0.9402,0.9441,0.9498,0.953,0.9541],"avgshortpasstry":[76.2765,76.4316,77.0041,76.8332,72.8024,73.5354,74.069,74.448,74.9056,75.0428,75.032,74.4688,74.6173,74.4106,75.2425,75.3019,76.0296,75.8331,75.1333,75.3505,75.4748,75.3273,75.915,75.3836,75.9461,75.8557,75.8646,76.5134,76.7147,75.7078],"avgshortpasssuccess":[72.4677,72.6471,73.2191,73.0717,69.037,69.7875,70.3218,70.709,71.1666,71.3231,71.3218,70.7972,70.9099,70.7261,71.5111,71.5724,72.2658,72.1046,71.4139,71.5963,71.69,71.5845,72.178,71.6453,72.1938,72.0709,72.0828,72.6804,72.9196,71.9721],"avglobpasstry":[4.76654,4.82643,4.85301,4.86572,4.83022,4.83719,4.80997,4.863,4.8826,4.8635,4.8637,4.8239,4.9191,4.8338,4.868,4.8575,4.7743,4.7402,4.8522,4.8581,4.8108,4.8466,4.8878,4.7719,4.8145,4.8599,4.8532,4.8802,4.8937,4.9914],"avglobpasssuccess":[2.72017,2.75123,2.77832,2.80149,2.65453,2.69882,2.70139,2.732,2.7608,2.7469,2.7484,2.7295,2.7947,2.7377,2.7526,2.7585,2.7061,2.6851,2.7404,2.7728,2.7127,2.7603,2.7854,2.6993,2.7234,2.7553,2.7461,2.7488,2.7525,2.8338],"avgdrivengroundpasstry":[3.74522,3.84308,3.80564,3.83749,3.40452,3.49445,3.53986,3.6211,3.6542,3.6387,3.6777,3.6819,3.6559,3.6981,3.7408,3.7396,3.7607,3.7547,3.9007,3.8517,3.711,3.8028,3.8553,3.8383,3.8345,3.8708,3.8718,3.7368,3.784,3.9505],"avgdrivengroundpasssuccess":[3.2226,3.32366,3.2953,3.3251,2.91518,3.00364,3.04173,3.1189,3.1561,3.1386,3.1782,3.1734,3.1571,3.1926,3.2276,3.2287,3.2506,3.2442,3.3755,3.3308,3.2049,3.2885,3.3377,3.3206,3.3176,3.3437,3.3506,3.2243,3.2676,3.4263],"avgthroughpasstry":[19.397,19.2388,19.0713,18.8569,20.1685,19.7509,19.8052,19.6501,19.4453,19.3324,19.2879,19.1511,19.3668,19.4174,19.5108,19.6634,19.2453,19.1215,19.4988,19.4172,19.5254,19.4108,19.0443,19.1242,19.1972,19.228,19.2948,19.4343,19.4803,19.4128],"avgthroughpasssuccess":[16.6293,16.5095,16.4018,16.1891,17.2178,16.8854,16.9806,16.8383,16.6661,16.5899,16.567,16.4338,16.6364,16.6664,16.7327,16.8945,16.5338,16.4468,16.7454,16.669,16.7739,16.6953,16.3602,16.405,16.4835,16.5007,16.5507,16.6919,16.737,16.68],"avglobbedthroughpasstry":[0.26541,0.25191,0.26219,0.25728,0.34414,0.30799,0.30179,0.296,0.3022,0.282,0.2791,0.2738,0.2684,0.2782,0.2847,0.281,0.2733,0.2713,0.2667,0.2609,0.2683,0.2538,0.2542,0.2663,0.2544,0.2584,0.2574,0.2652,0.2643,0.2692],"avglobbedthroughpasssuccess":[0.16955,0.16095,0.16622,0.16465,0.21468,0.19269,0.19116,0.1878,0.1875,0.1783,0.1762,0.1749,0.1732,0.1783,0.1829,0.1829,0.174,0.1751,0.1702,0.1676,0.1706,0.1616,0.1635,0.1713,0.1623,0.167,0.1641,0.1673,0.1695,0.1698],"avgcornerkick":[1.7502,1.73433,1.74214,1.71313,1.77713,1.77301,1.76685,1.7773,1.7555,1.7462,1.7559,1.7435,1.7481,1.7409,1.7433,1.7422,1.7198,1.7147,1.73,1.7291,1.7487,1.7454,1.7351,1.738,1.7453,1.7469,1.7602,1.7553,1.7717,1.7521],"avgycards":[0.04914,0.04691,0.04553,0.04736,0.06258,0.05639,0.05497,0.0541,0.0488,0.0504,0.0494,0.0489,0.052,0.051,0.0514,0.05,0.0503,0.0485,0.0477,0.0522,0.0489,0.049,0.0489,0.0492,0.0475,0.0487,0.0515,0.0478,0.0462,0.0465],"avgrcards":[0.00746,0.00806,0.00702,0.00746,0.0104,0.00889,0.00795,0.0084,0.0075,0.0069,0.0082,0.0079,0.0082,0.0082,0.008,0.0075,0.0074,0.0073,0.0076,0.0079,0.0078,0.0083,0.0081,0.0089,0.0072,0.0069,0.0081,0.0079,0.0073,0.0076],"avginjury":[0.11503,0.11635,0.11369,0.11821,0.11974,0.11983,0.11805,0.1188,0.1191,0.1165,0.1173,0.1155,0.118,0.1184,0.1181,0.1163,0.1181,0.1158,0.1152,0.1158,0.1184,0.1177,0.115,0.1179,0.1173,0.1195,0.1178,0.1177,0.1169,0.1166],"avgoffsidecnt":[0.51759,0.51422,0.50978,0.51652,0.53755,0.52855,0.52129,0.5158,0.5205,0.5116,0.5146,0.5193,0.5202,0.5129,0.5222,0.5196,0.5162,0.5131,0.5084,0.5174,0.5198,0.5143,0.512,0.516,0.5158,0.5089,0.5158,0.5198,0.5117,0.5202],"avgavgrating":[4.19915,4.19181,4.19113,4.19075,4.23356,4.23111,4.22957,4.22405,4.21713,4.20501,4.20777,4.20908,4.21681,4.21286,4.20929,4.20747,4.20503,4.20459,4.20063,4.20398,4.21146,4.20395,4.19664,4.19544,4.19888,4.19614,4.19822,4.20447,4.20125,4.19677]}
    
    data_2 = {"lengthDate":30,"date":["2024-12-08T00:00:00","2024-12-09T00:00:00","2024-12-10T00:00:00","2024-12-11T00:00:00","2024-12-12T00:00:00","2024-12-13T00:00:00","2024-12-14T00:00:00","2024-12-15T00:00:00","2024-12-16T00:00:00","2024-12-17T00:00:00","2024-12-18T00:00:00","2024-12-19T00:00:00","2024-12-20T00:00:00","2024-12-21T00:00:00","2024-12-22T00:00:00","2024-12-23T00:00:00","2024-12-24T00:00:00","2024-12-25T00:00:00","2024-12-26T00:00:00","2024-12-27T00:00:00","2024-12-28T00:00:00","2024-12-29T00:00:00","2024-12-30T00:00:00","2024-12-31T00:00:00","2025-01-01T00:00:00","2025-01-02T00:00:00","2025-01-03T00:00:00","2025-01-04T00:00:00","2025-01-05T00:00:00","2025-01-06T00:00:00"],"count":[220680,224446,221024,217559,172958,291737,270382,257153,257284,251766,245432,151888,246545,242304,233375,237394,235868,231795,231319,232088,229900,227855,230386,227115,223410,163185,233675,227521,229815,231247],"avggoaltot":[1.44615,1.45146,1.44774,1.45091,1.45712,1.40449,1.40205,1.4057,1.4066,1.4096,1.4157,1.4239,1.4129,1.42,1.4242,1.4281,1.4288,1.4278,1.4301,1.4325,1.4335,1.4336,1.4349,1.4337,1.4346,1.4325,1.4332,1.445,1.4373,1.4426],"avgshoottot":[4.71616,4.73197,4.7237,4.73943,4.50139,4.47113,4.48424,4.502,4.5184,4.5353,4.5595,4.525,4.5673,4.5993,4.6039,4.616,4.6303,4.6312,4.6367,4.6448,4.651,4.6679,4.676,4.6732,4.6681,4.6372,4.6791,4.6912,4.6886,4.7087],"avgeffshoottot":[3.68293,3.69542,3.68728,3.70026,3.53506,3.49774,3.50525,3.5197,3.5315,3.5452,3.5649,3.5464,3.5709,3.5953,3.5983,3.6106,3.6169,3.6216,3.6245,3.6295,3.6343,3.6446,3.6544,3.6528,3.6483,3.6257,3.655,3.6719,3.6629,3.679],"avggoalpenaltykick":[0.02619,0.0262,0.02605,0.02666,0.0258,0.02495,0.02491,0.0255,0.0252,0.0254,0.0251,0.0251,0.0255,0.0253,0.025,0.0253,0.0256,0.0255,0.0259,0.0256,0.0253,0.0255,0.0254,0.0256,0.0256,0.0253,0.0258,0.0259,0.0258,0.0256],"avggoalfreekick":[0.00315,0.00324,0.00329,0.00342,0.00336,0.00327,0.00324,0.0033,0.0032,0.0033,0.0033,0.0033,0.0033,0.0032,0.0031,0.0033,0.0032,0.0032,0.0034,0.0033,0.0031,0.0033,0.0033,0.0034,0.0032,0.0031,0.0034,0.0034,0.0033,0.0032],"avgshootinpenalty":[2.97522,2.98847,2.98068,2.99023,2.87035,2.82388,2.82929,2.8378,2.8476,2.8563,2.8718,2.8634,2.8784,2.8948,2.8992,2.9064,2.9162,2.9145,2.9179,2.917,2.9205,2.9306,2.9397,2.9353,2.93,2.9165,2.9359,2.9489,2.9435,2.958],"avggoalinpenalty":[1.1011,1.10591,1.10254,1.10359,1.11205,1.0688,1.0675,1.069,1.0715,1.0704,1.077,1.0852,1.0736,1.0806,1.0823,1.0872,1.0867,1.0861,1.0864,1.0869,1.0884,1.0888,1.0907,1.088,1.0872,1.0885,1.0861,1.0974,1.0915,1.0954],"avgshootoutpenalty":[1.7052,1.70737,1.70737,1.71287,1.596,1.613,1.62081,1.6294,1.6364,1.6442,1.6533,1.6273,1.6541,1.6697,1.6702,1.6749,1.6792,1.6818,1.6835,1.6927,1.6955,1.7021,1.7015,1.7028,1.703,1.6858,1.7079,1.7069,1.7095,1.7153],"avggoaloutpenalty":[0.31887,0.31935,0.31915,0.32066,0.31926,0.31075,0.30964,0.3112,0.3099,0.3137,0.3136,0.3136,0.3138,0.3141,0.3169,0.3156,0.3165,0.3163,0.3178,0.32,0.3197,0.3193,0.3188,0.3201,0.3218,0.3187,0.3213,0.3217,0.32,0.3216],"middleshoot":[18.6996,18.7041,18.6922,18.7204,20.0039,19.2652,19.1042,19.0974,18.9358,19.0786,18.9674,19.2681,18.9723,18.8108,18.9767,18.8451,18.849,18.8067,18.8776,18.9065,18.856,18.7589,18.7373,18.7985,18.8932,18.9043,18.8135,18.8453,18.7216,18.7504],"outpenaltygoalratio":[22.0493,22.0019,22.0444,22.1004,21.9105,22.1254,22.0849,22.1384,22.0318,22.2545,22.1516,22.024,22.2096,22.1197,22.2511,22.0993,22.1515,22.153,22.2222,22.3386,22.3021,22.2726,22.2176,22.3268,22.4313,22.2478,22.4184,22.263,22.264,22.2931],"avggoalheading":[0.17623,0.1771,0.17649,0.17543,0.17543,0.1718,0.16982,0.171,0.1711,0.171,0.1706,0.1729,0.1704,0.1728,0.1706,0.1728,0.173,0.1737,0.174,0.1744,0.1725,0.1737,0.173,0.1722,0.1731,0.1734,0.1726,0.1738,0.1742,0.1737],"goalheadingratio":[12.1864,12.2017,12.1909,12.0912,12.0398,12.2321,12.1122,12.1663,12.1659,12.1315,12.0488,12.1442,12.0634,12.1676,11.9794,12.1009,12.1054,12.1685,12.1637,12.1746,12.0368,12.1185,12.0556,12.0125,12.0652,12.1013,12.0397,12.0292,12.123,12.0442],"avgpasstry":[107.291,107.846,107.82,108.055,99.9774,99.684,100.554,101.386,102.094,102.874,103.245,102.521,103.729,104.536,104.54,105.098,105.445,105.754,105.902,106.24,106.447,106.667,106.897,107.101,107.154,106.496,107.449,107.66,107.74,108.266],"avgpasssuccess":[92.829,93.3194,93.3212,93.5106,86.4914,86.2143,86.9649,87.6975,88.3307,89.0226,89.3016,88.6802,89.7365,90.464,90.4396,90.9277,91.2546,91.5662,91.6876,91.9716,92.1748,92.3644,92.559,92.7478,92.8008,92.2472,93.061,93.2686,93.3337,93.8054],"passsuccessratio":[86.5208,86.5303,86.5524,86.5397,86.5109,86.4876,86.4858,86.4983,86.5186,86.5355,86.4952,86.4994,86.5106,86.5382,86.512,86.517,86.5422,86.5841,86.5776,86.5695,86.5927,86.5913,86.5872,86.5983,86.6051,86.6206,86.6093,86.6329,86.6289,86.6436],"avgowngoal":[0.00711,0.00706,0.00704,0.00726,0.00615,0.00633,0.00646,0.0067,0.0065,0.0067,0.0067,0.0066,0.0068,0.0069,0.0067,0.0066,0.0068,0.0069,0.0068,0.0068,0.0067,0.0071,0.0071,0.007,0.007,0.0068,0.0071,0.0069,0.0071,0.0069],"avgpossession":[49.9235,49.9198,49.9283,49.9287,49.6531,49.7601,49.8087,49.8289,49.8326,49.8605,49.8582,49.8212,49.8724,49.8825,49.8773,49.8886,49.8971,49.8798,49.8867,49.8898,49.8991,49.9057,49.9036,49.9012,49.9105,49.9013,49.9182,49.9244,49.9251,49.9284],"avgdribble":[83.3109,83.7468,83.7147,83.8795,76.9218,76.9876,77.8102,78.5076,79.1054,79.7429,80.0403,79.2849,80.4684,81.1429,81.1437,81.5962,81.8677,82.1295,82.2255,82.5304,82.7413,82.9151,83.0839,83.2464,83.3038,82.6746,83.5419,83.7277,83.8135,84.2164],"avgtacklesuccess":[5.49213,5.5055,5.49448,5.50985,5.18386,5.18148,5.22452,5.2537,5.2765,5.304,5.3224,5.2794,5.3434,5.375,5.3792,5.4074,5.4071,5.4015,5.4095,5.4417,5.4427,5.4469,5.4557,5.4575,5.4591,5.4298,5.4699,5.4891,5.4825,5.5028],"avgtackletry":[8.11323,8.13544,8.12004,8.13878,7.66839,7.6505,7.7092,7.7561,7.7895,7.8251,7.861,7.8014,7.8901,7.9322,7.9432,7.9804,7.9846,7.9811,7.9962,8.0348,8.0345,8.0394,8.0573,8.0581,8.064,8.0153,8.075,8.0962,8.0895,8.1217],"avgblocksuccess":[0.42877,0.42905,0.42834,0.4291,0.39628,0.39797,0.40462,0.4046,0.409,0.4098,0.4112,0.4081,0.4119,0.4159,0.4163,0.418,0.4187,0.4202,0.4208,0.4232,0.4213,0.4246,0.4247,0.4235,0.4237,0.4212,0.4262,0.4243,0.4254,0.4284],"avgblocktry":[7.0345,7.05604,7.05243,7.06326,6.55668,6.57458,6.64273,6.6797,6.7224,6.7616,6.7884,6.7322,6.814,6.8532,6.8665,6.8904,6.9043,6.9072,6.9239,6.9525,6.9507,6.9706,6.9875,6.9936,6.9949,6.9421,7.0094,7.0058,7.0117,7.0455],"avgfoul":[0.7951,0.79742,0.7946,0.79671,0.74294,0.74585,0.75407,0.76,0.7637,0.766,0.77,0.7657,0.7738,0.7783,0.7818,0.7806,0.7839,0.7825,0.7854,0.7869,0.7877,0.7884,0.7912,0.7924,0.7908,0.7835,0.7944,0.7948,0.7943,0.797],"avgshootfreekick":[0.08566,0.08692,0.08618,0.08684,0.08157,0.08081,0.08204,0.0819,0.083,0.0824,0.0837,0.0825,0.083,0.0845,0.0845,0.0849,0.0851,0.0849,0.0851,0.0851,0.0856,0.0863,0.0856,0.0866,0.085,0.0846,0.0856,0.0864,0.0855,0.0866],"avgshootpenaltykick":[0.03349,0.0339,0.03337,0.03418,0.0328,0.03209,0.03206,0.0327,0.0324,0.0327,0.0323,0.0322,0.0326,0.0326,0.0324,0.0325,0.0328,0.0327,0.0332,0.0328,0.0328,0.033,0.0327,0.033,0.0329,0.0327,0.0333,0.0332,0.0333,0.0331],"avgshootheading":[0.90152,0.90624,0.90429,0.90474,0.85474,0.85449,0.85212,0.8571,0.8565,0.8613,0.8636,0.8561,0.8691,0.8739,0.8714,0.8757,0.8805,0.8785,0.8804,0.8799,0.8808,0.8854,0.8864,0.8868,0.8833,0.8754,0.8873,0.8866,0.8876,0.8921],"avgshortpasstry":[63.1295,63.4958,63.5381,63.6519,58.6973,58.5421,59.0719,59.6117,60.0912,60.5989,60.7242,60.279,61.0238,61.5566,61.5255,61.8696,62.1252,62.4212,62.4761,62.6771,62.8534,63.0026,63.1127,63.3007,63.3357,62.9534,63.5351,63.6583,63.699,64.0251],"avgshortpasssuccess":[61.3055,61.6617,61.7084,61.8195,56.9842,56.8333,57.3505,57.879,58.3523,58.8523,58.9661,58.532,59.2615,59.7824,59.7502,60.0869,60.3351,60.6321,60.6834,60.8763,61.054,61.2012,61.3026,61.488,61.5265,61.1571,61.7218,61.845,61.8843,62.2044],"avglobpasstry":[6.64584,6.67108,6.64376,6.66689,6.18781,6.14937,6.19447,6.2423,6.2688,6.3104,6.3541,6.3137,6.3779,6.4177,6.4254,6.4443,6.46,6.4624,6.482,6.4853,6.4967,6.5141,6.5313,6.53,6.5208,6.4688,6.5402,6.5324,6.5404,6.5687],"avglobpasssuccess":[2.1493,2.1564,2.14745,2.15134,2.03326,2.00906,2.01514,2.0282,2.0326,2.0416,2.0499,2.0404,2.0597,2.072,2.066,2.0742,2.0838,2.0806,2.0909,2.0879,2.0916,2.0978,2.1028,2.1038,2.097,2.0785,2.1014,2.1019,2.101,2.1141],"avgdrivengroundpasstry":[4.70005,4.72835,4.73261,4.73855,4.32257,4.34846,4.37875,4.4202,4.4548,4.4918,4.5161,4.482,4.5461,4.6007,4.5939,4.6209,4.6332,4.6544,4.6633,4.6735,4.6745,4.6981,4.7044,4.7139,4.7194,4.6923,4.7366,4.7448,4.7597,4.7854],"avgdrivengroundpasssuccess":[4.54526,4.57275,4.57805,4.58468,4.17898,4.204,4.2338,4.2752,4.3082,4.3433,4.368,4.3347,4.3969,4.4509,4.443,4.4694,4.4809,4.5026,4.5109,4.5211,4.5213,4.5446,4.5512,4.5603,4.5656,4.5386,4.5831,4.5904,4.6053,4.6301],"avgthroughpasstry":[22.9967,23.0851,23.0501,23.1093,21.6636,21.5257,21.7356,21.8776,22.009,22.1481,22.2624,22.1517,22.3541,22.4924,22.5003,22.6109,22.6675,22.6568,22.7185,22.8027,22.8293,22.8287,22.9129,22.9109,22.9265,22.7951,22.968,23.0437,23.0558,23.1605],"avgthroughpasssuccess":[19.3414,19.4178,19.3903,19.4398,18.2057,18.0735,18.2562,18.3777,18.4878,18.6129,18.7097,18.6131,18.79,18.9127,18.914,19.0061,19.0567,19.0571,19.1097,19.1761,19.2052,19.1982,19.2751,19.2718,19.2844,19.1749,19.323,19.3865,19.3954,19.4905],"avglobbedthroughpasstry":[8.97157,9.01604,9.00856,9.03576,8.29667,8.31351,8.36586,8.4219,8.4573,8.5066,8.566,8.4747,8.6026,8.6411,8.6663,8.7201,8.7254,8.73,8.7276,8.7656,8.7573,8.7849,8.8009,8.8092,8.8107,8.7543,8.8279,8.8365,8.8441,8.882],"avglobbedthroughpasssuccess":[5.31662,5.33957,5.3258,5.3429,4.92149,4.93088,4.94681,4.9743,4.9859,5.0082,5.0433,4.9949,5.0629,5.0802,5.0997,5.1251,5.1304,5.1274,5.1257,5.1426,5.1349,5.1544,5.1602,5.1565,5.1599,5.1327,5.1643,5.1757,5.1794,5.1976],"avgcornerkick":[1.82745,1.83233,1.82892,1.8368,1.69281,1.70477,1.71659,1.7265,1.7372,1.7465,1.7584,1.7374,1.7643,1.7779,1.7772,1.7826,1.7881,1.7943,1.7927,1.7933,1.8012,1.807,1.8112,1.8134,1.8046,1.7922,1.8163,1.8142,1.818,1.8271],"avgycards":[0.08049,0.08171,0.08149,0.08152,0.07658,0.07619,0.07786,0.0782,0.0786,0.0792,0.0789,0.0775,0.0792,0.0798,0.0806,0.0795,0.0807,0.0803,0.0811,0.0808,0.0815,0.0803,0.0815,0.0819,0.0814,0.0806,0.0818,0.0826,0.0815,0.0819],"avgrcards":[0.00317,0.00337,0.00314,0.00325,0.00276,0.00291,0.00292,0.0029,0.0029,0.003,0.0031,0.0032,0.003,0.003,0.0031,0.0032,0.003,0.0033,0.0031,0.0031,0.0031,0.0033,0.0031,0.0031,0.0033,0.0033,0.0032,0.0032,0.0031,0.0035],"avginjury":[0.14441,0.14357,0.14389,0.14537,0.13573,0.13425,0.13533,0.1376,0.1373,0.1381,0.1392,0.1382,0.14,0.1396,0.1398,0.1398,0.1406,0.1411,0.142,0.1423,0.1423,0.1414,0.1434,0.1432,0.1424,0.1423,0.1427,0.1443,0.1444,0.1443],"avgoffsidecnt":[1.67401,1.67923,1.67661,1.68811,1.54013,1.55936,1.56564,1.5751,1.5846,1.5928,1.6043,1.586,1.6149,1.625,1.6285,1.6393,1.6383,1.6446,1.6461,1.6512,1.6532,1.6579,1.6607,1.6649,1.6622,1.6485,1.6708,1.6774,1.6714,1.6816],"avgavgrating":[4.00688,4.00632,4.00584,4.006,4.03015,4.01485,4.01118,4.00985,4.00837,4.00845,4.00825,4.01195,4.00705,4.00767,4.00714,4.00654,4.00715,4.00676,4.00662,4.00599,4.00599,4.00555,4.00512,4.00466,4.00494,4.00667,4.00421,4.00625,4.00422,4.00401]}

    # 데이터를 DataFrame으로 변환
    if match_type == "52":
        df = pd.DataFrame(data_2)
    else:
        df = pd.DataFrame(data_1)
    # 마지막 행 반환
    return df.iloc[-1, :]

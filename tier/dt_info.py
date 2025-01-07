# 각 포지션 별 XPATH
XPATHS = {
    "ST" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[1]/div[2]/div[2]/label',
    "CF" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[1]/div[2]/div[3]/label',
    "LW" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[1]/div[2]/div[4]/label',
    "RW" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[1]/div[2]/div[5]/label',
    "CAM" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[2]/div[2]/div[3]/label', 
    "CM" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[2]/div[2]/div[2]/label', 
    "CDM" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[2]/div[2]/div[4]/label', 
    "CB" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[3]/div[2]/div[2]/label', 
    "LB" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[3]/div[2]/div[4]/label', 
    "RB" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[3]/div[2]/div[3]/label', 
    "GK" : '//*[@id="form1"]/div[3]/div[2]/div[2]/div[4]/div[2]/div/label'
}

# 각 포지션 별 op threshold
pos_threshold = {
    "ST" : 10,
    "CF" : 13, 
    "LW" : 14, 
    "RW" : 14, 
    "CAM" : 15, 
    "CM" : 14, 
    "CDM" : 11, 
    "CB" : 14, 
    "LB" : 16, 
    "RB" : 15, 
    "GK" : 14
}

# 열 이름과 데이터를 매칭할 딕셔너리 (한국어 버전)
column_mapping = {
    '출전': 'p_at',                  
    '공격 포인트': 'p_atp',         
    '득점' : 'p_g',
    '도움' : 'p_as',
    '유효 슛': 'p_pg',                
    '슛' : 'p_ng',
    '패스 성공률': 'p_p',         
    '드리블 성공률': 'p_d',        
    '공중볼 경합 성공률' : 'p_s',
    '가로채기' : 'p_df',
    '태클 성공률': 'p_tt',          
    '차단 성공률' : 'p_td',
    '선방(골 차단)' : 'p_tk',
    '평점' : 'p_av'
} 

# # 수동 크롤링 정보 저장용
# cr_info = {
#     "ST" : '''
#     ''',
#     "CF" : '''
#     ''',
#     "LW" : '''
#     ''',
#     "RW" : '''
#     ''',
#     "CAM" : '''
#     ''',
#     "CM" : '''
#     ''',
#     "CDM" : '''
#     ''',
#     "CB" :'''
#     ''',
#     "LB" : '''
#     ''',
#     "RB" : '''
#     ''',
#     "GK" : '''
#     '''
# }

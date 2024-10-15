from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score
from sklearn.utils import resample
import numpy as np

# 데이터 증강 함수
def augment_data(X, y, random_state=42):
    win_data = [x for x, label in zip(X, y) if label == '승']
    lose_data = [x for x, label in zip(X, y) if label == '패']
    draw_data = [x for x, label in zip(X, y) if label == '무']

    win_count, lose_count, draw_count = len(win_data), len(lose_data), len(draw_data)

    win_data_resampled = np.array(resample(win_data, replace=True, n_samples=win_count * 3, random_state=random_state)) if win_count > 0 else np.array(win_data)
    lose_data_resampled = np.array(resample(lose_data, replace=True, n_samples=lose_count * 3, random_state=random_state)) if lose_count > 0 else np.array(lose_data)
    draw_data_resampled = np.array(resample(draw_data, replace=True, n_samples=draw_count * 3, random_state=random_state)) if draw_count > 0 else np.array(draw_data)

    resampled_data = [win_data_resampled, lose_data_resampled, draw_data_resampled]
    resampled_data = [data for data in resampled_data if len(data) > 0]

    if len(resampled_data) > 0 and all(data.shape[1] == resampled_data[0].shape[1] for data in resampled_data):
        X_resampled = np.vstack(resampled_data)
        y_resampled = ['승'] * len(win_data_resampled) + ['패'] * len(lose_data_resampled) + ['무'] * len(draw_data_resampled)
        print(f"승: {len(win_data_resampled)}개, 패: {len(lose_data_resampled)}개, 무: {len(draw_data_resampled)}개로 증강 완료")
        return X_resampled, y_resampled
    else:
        raise ValueError("모든 클래스 데이터의 열 수가 같지 않거나 데이터가 부족합니다.")

def rf_train(original_win_rate, imp_data, w_l_data, data_label, t_s, n_es, max_d, mss, msl, min_inc, max_inc, min_win, max_win):
    # 데이터 분할
    X_train, X_test, y_train, y_test = train_test_split(imp_data, w_l_data, test_size=t_s, random_state=42)

    # NaN 값 처리
    imputer = SimpleImputer(strategy='constant', fill_value=0)
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    # 랜덤 포레스트 모델 정의 (기본 파라미터)
    rf = RandomForestClassifier(n_estimators=n_es, max_depth=max_d, bootstrap = False, min_samples_split = mss, min_samples_leaf = msl, random_state=42)
    rf.fit(X_train_imputed, y_train)

    y_pred = rf.predict(X_test_imputed)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Random Forest 모델의 정확도: {accuracy * 100:.2f}%")

    # 상위 N개의 중요한 특성에 대해 승률 개선 계산
    for top_n in range(2, 11):
        importances = np.abs(rf.feature_importances_)
        indices = np.argsort(importances)[::-1]
        top_features_indices = indices[:top_n]

        for increase_ratio in np.arange(min_inc, max_inc, 0.001):
            X_test_modified = X_test_imputed.copy()
            original_feature_values = X_test_imputed.mean(axis=0)
            modified_feature_values = original_feature_values.copy()

            for idx in top_features_indices:
                X_test_modified[:, idx] *= (1 + increase_ratio)
                modified_feature_values[idx] = original_feature_values[idx] * (1 + increase_ratio)

            y_pred_modified = rf.predict(X_test_modified)
            modified_win_count = sum(1 for result in y_pred_modified if result == '승')
            modified_win_rate = modified_win_count / len(y_pred_modified)
            win_rate_improvement = modified_win_rate - original_win_rate

            if min_win <= win_rate_improvement <= max_win and modified_win_rate < 1:
                improved_features = [data_label[i] for i in top_features_indices]
                improved_features_text = "\n".join([
                    f"{feature}: {original_feature_values[i]:.2f} -> {modified_feature_values[i]:.2f}"
                    for feature, i in zip(improved_features, top_features_indices)
                ])
                return top_n, increase_ratio, improved_features_text, original_win_rate, modified_win_rate, win_rate_improvement
        
    return 0, 0, "", original_win_rate, original_win_rate, 0
                

# 승률 개선 계산 함수
def calculate_win_improvement(imp_data, w_l_data, data_label, random_state=42):
    imp_data, w_l_data = augment_data(imp_data, w_l_data, random_state=random_state)

    win_count = sum(1 for result in w_l_data if result == '승')
    original_win_rate = win_count / len(w_l_data)

    if original_win_rate > 0.5:
        return rf_train(original_win_rate = original_win_rate, imp_data = imp_data, w_l_data = w_l_data, data_label = data_label, 
        t_s = 0.25, n_es = 7, max_d = 5, mss = 0.17, msl = 0.17, min_inc = 0.03, max_inc = 0.7, min_win = 0.01, max_win = 0.4)
    elif original_win_rate <= 0.5:
        return rf_train(original_win_rate = original_win_rate, imp_data = imp_data, w_l_data = w_l_data, data_label = data_label, 
        t_s= 0.2, n_es = 10, max_d = 5, mss = 0.1, msl = 0.1, min_inc = 0.05, max_inc = 0.7, min_win = 0.01, max_win = 0.6)
    

# 실험용 (wr_result에 2개 수정)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np

def calculate_win_improvement(imp_data, w_l_data, data_label, who_is_next):
    # 데이터 분할
    X_train, X_test, y_train, y_test = train_test_split(imp_data, w_l_data, test_size=0.2, random_state=42)

    # NaN 값 처리
    imputer = SimpleImputer(strategy='mean')
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    # RandomizedSearchCV에서 사용할 하이퍼파라미터 공간 정의 (로지스틱 회귀 하이퍼파라미터)
    param_distributions = {
        'C': np.logspace(-4, 4, 20),  # 규제 강도
        'penalty': ['l1', 'l2'],      # 페널티 유형
        'solver': ['liblinear']       # L1 페널티를 지원하는 solver
    }

    # 원하는 정확도에 도달할 때까지 반복
    accuracy = 0
    iteration_count = 0  # 몇 번의 시도를 했는지 기록하기 위한 변수

    while accuracy < 0.7:
        iteration_count += 1
        print(f"\n{iteration_count}번째 시도 중...")

        # Logistic Regression 모델과 RandomizedSearchCV 설정
        model = LogisticRegression()
        random_search = RandomizedSearchCV(
            model, 
            param_distributions, 
            n_iter=10,  # 총 10개의 하이퍼파라미터 조합 시도
            scoring='accuracy', 
            cv=3  # 교차 검증 횟수
        )

        # 모델 학습 및 하이퍼파라미터 튜닝
        random_search.fit(X_train_imputed, y_train)

        # 최적의 모델로 예측
        best_model = random_search.best_estimator_
        y_pred = best_model.predict(X_test_imputed)

        # 정확도 평가
        accuracy = accuracy_score(y_test, y_pred)
        print(f"현재 모델의 정확도: {accuracy * 100:.2f}%")

        # 정확도 0.8 이상 도달 시 정보 출력
        if accuracy >= 0.8:
            print("\n목표 정확도에 도달했습니다!")
            print(f"\n최적 모델의 정확도: {accuracy * 100:.2f}%")
            print("최적 하이퍼파라미터 조합:", random_search.best_params_)
            # 최적 모델
            best_model = random_search.best_estimator_

    # 원래 승률 계산
    win_count = sum(1 for result in w_l_data if result == '승')
    original_win_rate = win_count / len(w_l_data)

    # 파라미터 조합 시도
    for top_n in range(3, 11):  # 상위 3개부터 10개까지 시도
        importances = np.abs(best_model.coef_[0])
        indices = np.argsort(importances)[::-1]
        top_features_indices = indices[:top_n]

        for increase_ratio in np.arange(0.1, 0.7, 0.1):  # 10%씩 증가, 최대 60%
            # 상위 top_n 개 지표 increase_ratio만큼 증가
            X_test_modified = X_test_imputed.copy()
            original_feature_values = X_test_imputed.mean(axis=0)
            modified_feature_values = original_feature_values.copy()

            for idx in top_features_indices:
                X_test_modified[:, idx] *= (1 + increase_ratio)
                modified_feature_values[idx] = original_feature_values[idx] * (1 + increase_ratio)

            # 수정된 데이터로 예측
            y_pred_modified = best_model.predict(X_test_modified)

            # 수정된 데이터의 승률 계산
            modified_win_count = sum(1 for result in y_pred_modified if result == '승')
            modified_win_rate = modified_win_count / len(y_pred_modified)
            win_rate_improvement = modified_win_rate - original_win_rate

            # 승률이 5% 이상 30% 이하로 증가했을 경우
            if 0.05 <= win_rate_improvement <= 0.40:
                improved_features = [data_label[i] for i in top_features_indices]
                improved_features_text = "\n".join([
                    f"{feature}: {original_feature_values[i]:.2f} -> {modified_feature_values[i]:.2f}"
                    for feature, i in zip(improved_features, top_features_indices)
                ])

                return top_n, increase_ratio, improved_features_text, original_win_rate, modified_win_rate, win_rate_improvement
                break
        if 0.05 <= win_rate_improvement <= 0.30:
            break

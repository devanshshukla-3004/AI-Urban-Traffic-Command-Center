import json
from pathlib import Path
import joblib, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE=Path(__file__).resolve().parent; DATA=BASE/'data/synthetic_traffic_data.csv'; MODELS=BASE/'models'; MODELS.mkdir(exist_ok=True)

def main():
    df=pd.read_csv(DATA)
    features=['hour','day_of_week','weather','road','vehicle_count']; X=df[features]; y=df['congestion_level']
    cat=['weather','road','day_of_week']; num=['hour','vehicle_count']
    prep=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore'),cat)],remainder='passthrough')
    clf=Pipeline([('prep',prep),('model',RandomForestClassifier(n_estimators=200,max_depth=12,random_state=42,n_jobs=-1,class_weight='balanced'))])
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=42,stratify=y); clf.fit(Xtr,ytr); pred=clf.predict(Xte)
    metrics={'accuracy':accuracy_score(yte,pred),'precision_weighted':precision_score(yte,pred,average='weighted',zero_division=0),'recall_weighted':recall_score(yte,pred,average='weighted',zero_division=0),'f1_weighted':f1_score(yte,pred,average='weighted',zero_division=0),'confusion_matrix':confusion_matrix(yte,pred).tolist(),'classes':sorted(y.unique().tolist())}
    joblib.dump(clf,MODELS/'congestion_model.joblib'); (MODELS/'metrics.json').write_text(json.dumps(metrics,indent=2)); (MODELS/'label_classes.json').write_text(json.dumps(metrics['classes']))
    # Separate demand forecaster for the decision horizon.
    xf=df[['hour','day_of_week','weather','road']]; yf=df['vehicle_count']; p2=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore'),['weather','road','day_of_week'])],remainder='passthrough')
    reg=Pipeline([('prep',p2),('model',RandomForestRegressor(n_estimators=180,max_depth=14,random_state=42,n_jobs=-1))]); a,b,c,d=train_test_split(xf,yf,test_size=.2,random_state=42); reg.fit(a,c); rp=reg.predict(b)
    joblib.dump(reg,MODELS/'traffic_forecaster.joblib'); f={'mae_synthetic':float(mean_absolute_error(d,rp))}; (MODELS/'forecast_metrics.json').write_text(json.dumps(f,indent=2))
    print(json.dumps(metrics,indent=2)); print('Forecast MAE:',round(f['mae_synthetic'],3)); print('Saved classifier + demand forecaster.')
if __name__=='__main__': main()

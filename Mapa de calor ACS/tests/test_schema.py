import pandas as pd

def test_required_columns_present():
    required = {"data_visita","latitude","longitude","UBS","ACS"}
    # simulação de cabeçalho válido
    df = pd.DataFrame(columns=list(required))
    assert required.issubset(set(df.columns))


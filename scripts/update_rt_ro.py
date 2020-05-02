import pandas as pd
import numpy as np
import json, urllib, ssl

from scipy import stats as sps

FILTERED_REGIONS = []

FILTERED_REGION_CODES = ['-', 'BR', 'BZ', 'CL', 'MH', 'MM', 'PH', 'SJ', 'VN']


def highest_density_interval(pmf, p=.9):
    # If we pass a DataFrame, just call this recursively on the columns
    if isinstance(pmf, pd.DataFrame):
        return pd.DataFrame([highest_density_interval(pmf[col], p=p) for col in pmf],
                            index=pmf.columns)
    cumsum = np.cumsum(pmf.values)
    total_p = cumsum - cumsum[:, None]
    lows, highs = (total_p > p).nonzero()
    best = (highs - lows).argmin()
    low = pmf.index[lows[best]]
    high = pmf.index[highs[best]]
    return pd.Series([low, high],
                     index=[f'Low_{p * 100:.0f}',
                            f'High_{p * 100:.0f}'])


# Get data for Romania
url = 'https://api1.datelazi.ro/api/v2/data'
with urllib.request.urlopen(url,
                            context=ssl._create_unverified_context()) as url:
    json_dz = json.loads(url.read().decode('Latin-1'))

json_dz = json_dz['historicalData']
dz = pd.DataFrame.from_dict(json_dz, orient='index')
dz.insert(0, 'date', dz.index)
dz = dz[['date', 'countyInfectionsNumbers']]
dz.loc[['20202-04-07'], ['date']] = '2020-04-07'
dz.loc[['20202-04-06'], ['date']] = '2020-04-06'
dz['date'] = pd.to_datetime(dz['date'])
dz = dz[dz['date'] >= '2020-04-02'].sort_values(by='date').reset_index(drop=True)

df = pd.DataFrame()
for index, row in dz.iterrows():
    df_temp = pd.DataFrame.from_dict(row['countyInfectionsNumbers'],
                                     orient='index',
                                     columns=['positive'])
    df_temp.insert(0, 'date', row['date'])
    df_temp.insert(1, 'state', df_temp.index)
    df = df.append(df_temp)

df = df.reset_index(drop=True)
df.to_csv('ro_data_latest.csv')

url = 'ro_data_latest.csv'
states = pd.read_csv(url,
                     usecols=['date', 'state', 'positive'],
                     parse_dates=['date'],
                     index_col=['state', 'date'],
                     squeeze=True).sort_index()

state_name = 'B'


def prepare_cases(cases, cutoff=1):
    new_cases = cases.diff()
    smoothed = new_cases.rolling(7,
                                 win_type='gaussian',
                                 min_periods=1,
                                 center=True).mean(std=2).round()
    idx_start = np.searchsorted(smoothed, cutoff)
    smoothed = smoothed.iloc[idx_start:]
    original = new_cases.loc[smoothed.index]
    return original, smoothed


cases = states.xs(state_name).rename(f"{state_name} cases")
original, smoothed = prepare_cases(cases)

R_T_MAX = 12
r_t_range = np.linspace(0, R_T_MAX, R_T_MAX*100+1)
GAMMA = 1/7

def get_posteriors(sr, sigma=0.15):
    lam = sr[:-1].values * np.exp(GAMMA * (r_t_range[:, None] - 1))
    likelihoods = pd.DataFrame(
        data=sps.poisson.pmf(sr[1:].values, lam),
        index=r_t_range,
        columns=sr.index[1:])
    process_matrix = sps.norm(loc=r_t_range,
                              scale=sigma
                              ).pdf(r_t_range[:, None])
    process_matrix /= process_matrix.sum(axis=0)
    prior0 = sps.gamma(a=4).pdf(r_t_range)
    prior0 /= prior0.sum()
    posteriors = pd.DataFrame(
        index=r_t_range,
        columns=sr.index,
        data={sr.index[0]: prior0}
    )
    log_likelihood = 0.0
    for previous_day, current_day in zip(sr.index[:-1], sr.index[1:]):
        current_prior = process_matrix @ posteriors[previous_day]
        numerator = likelihoods[current_day] * current_prior
        denominator = np.sum(numerator)
        posteriors[current_day] = numerator / denominator
        log_likelihood += np.log(denominator)
    return posteriors, log_likelihood
posteriors, log_likelihood = get_posteriors(smoothed, sigma=.25)

hdis = highest_density_interval(posteriors, p=.9)
most_likely = posteriors.idxmax().rename('ML')
result = pd.concat([most_likely, hdis], axis=1)
sigmas = np.linspace(1 / 20, 1, 20)
targets = ~states.index.get_level_values('state').isin(FILTERED_REGION_CODES)
states_to_process = states.loc[targets]
results = {}
for state_name, cases in states_to_process.groupby(level='state'):
    print(state_name)
    new, smoothed = prepare_cases(cases, cutoff=1)  # cutoff=25 in original notebook
    if len(smoothed) == 0:
        new, smoothed = prepare_cases(cases, cutoff=1)  # cutoff=10 in original notebook

    result = {}
    result['posteriors'] = []
    result['log_likelihoods'] = []
    for sigma in sigmas:
        posteriors, log_likelihood = get_posteriors(smoothed, sigma=sigma)
        result['posteriors'].append(posteriors)
        result['log_likelihoods'].append(log_likelihood)
    results[state_name] = result

total_log_likelihoods = np.zeros_like(sigmas)
for state_name, result in results.items():
    total_log_likelihoods += result['log_likelihoods']

max_likelihood_index = total_log_likelihoods.argmax()
sigma = sigmas[max_likelihood_index]

# LAST STEP

final_results = None
for state_name, result in results.items():
    print(state_name)
    posteriors = result['posteriors'][max_likelihood_index]
    hdis_90 = highest_density_interval(posteriors, p=.9)
    hdis_50 = highest_density_interval(posteriors, p=.5)
    most_likely = posteriors.idxmax().rename('ML')
    result = pd.concat([most_likely, hdis_90, hdis_50], axis=1)
    if final_results is None:
        final_results = result
    else:
        final_results = pd.concat([final_results, result])

final_results.to_csv('ro_rt_latest.csv')
print('Done.')

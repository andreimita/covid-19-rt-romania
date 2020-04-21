# covid-19-rt-romania #

Jupyter Notebooks for estimating COVID-19's Rt in Real-Time for counties, NUTS 3 (*județe*), in Romania and countries around the world. Based on the notebook published by Kevin Systrom for US. Original notebook available here: https://github.com/k-sys/covid-19

**data/ro_data_latest.csv**  
Extracted and processed data for Romania from [https://datelazi.ro](https://datelazi.ro)  to be used with ```Realtime R0 - Romania.ipynb```

**data/ro_rt_latest.csv**  
Computed Rt data for Romania based on date from ```data/ro_data_latest.csv```

**data/us_raw_data_latest.csv**  
Raw data for US states to be used with the original notebook ```Realtime R0 - Original.ipynb```

**img/ro_rt_latest.png**  
Resulted graphs for each county in Romania (except the ones that can't be processed due to lack or poor data).

**tableau/book.twb**
Tableau visualization with date from ```data/ro_data_latest.csv``` and ```data/ro_rt_latest.csv``` also available on [Tableau Public](https://public.tableau.com/views/book_15874671877920/Romnia?:display_count=y&publish=yes&:origin=viz_share_link).  

**tableau/data_extract.hyper**  
Data extract used by the Tableau visualization.
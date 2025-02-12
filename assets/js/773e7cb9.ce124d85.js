"use strict";(self.webpackChunkmy_docs=self.webpackChunkmy_docs||[]).push([[496],{913:(e,n,t)=>{t.r(n),t.d(n,{assets:()=>o,contentTitle:()=>l,default:()=>h,frontMatter:()=>r,metadata:()=>s,toc:()=>c});const s=JSON.parse('{"id":"tutorial-basics/User Guide","title":"Walkthrough","description":"---","source":"@site/docs/tutorial-basics/User Guide.md","sourceDirName":"tutorial-basics","slug":"/tutorial-basics/User Guide","permalink":"/murray/docs/tutorial-basics/User Guide","draft":false,"unlisted":false,"editUrl":"https://github.com/entropyx/murray/edit/documentation/docs/tutorial-basics/User Guide.md","tags":[],"version":"current","sidebarPosition":2,"frontMatter":{"sidebar_position":2},"sidebar":"tutorialSidebar","previous":{"title":"Install Python","permalink":"/murray/docs/tutorial-basics/Installation"},"next":{"title":"Streamlit Murray App","permalink":"/murray/docs/category/streamlit-murray-app"}}');var a=t(4848),i=t(8453);const r={sidebar_position:2},l="Walkthrough",o={},c=[{value:"Experimental Design",id:"experimental-design",level:2},{value:"1. Upload data",id:"1-upload-data",level:3},{value:"Cleaned data",id:"cleaned-data",level:4},{value:"2. Experimental desing",id:"2-experimental-desing",level:3},{value:"3. Results",id:"3-results",level:3},{value:"Treatment and control groups",id:"treatment-and-control-groups",level:4},{value:"Impact graphs",id:"impact-graphs",level:4},{value:"Weights",id:"weights",level:4},{value:"Incremental results",id:"incremental-results",level:3},{value:"Metrics",id:"metrics",level:3},{value:"Experimental Evaluation",id:"experimental-evaluation",level:2},{value:"1. Data",id:"1-data",level:3},{value:"2. Experimental evaluation",id:"2-experimental-evaluation",level:3},{value:"3. Results",id:"3-results-1",level:3},{value:"Impact graph",id:"impact-graph",level:4},{value:"Incremental results",id:"incremental-results-1",level:4},{value:"Permutation test",id:"permutation-test",level:4}];function d(e){const n={admonition:"admonition",code:"code",h1:"h1",h2:"h2",h3:"h3",h4:"h4",header:"header",hr:"hr",li:"li",p:"p",pre:"pre",ul:"ul",...(0,i.R)(),...e.components};return(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(n.header,{children:(0,a.jsx)(n.h1,{id:"walkthrough",children:"Walkthrough"})}),"\n",(0,a.jsx)(n.hr,{}),"\n",(0,a.jsx)(n.p,{children:"This guide constains an overview of Package Murray, as well as instructions for your used."}),"\n",(0,a.jsx)(n.h2,{id:"experimental-design",children:"Experimental Design"}),"\n",(0,a.jsx)(n.h3,{id:"1-upload-data",children:"1. Upload data"}),"\n",(0,a.jsx)(n.p,{children:"First, you need to read data with Pandas:"}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:'data = pd.read_csv("data.csv")\n'})}),"\n",(0,a.jsx)(n.h4,{id:"cleaned-data",children:"Cleaned data"}),"\n",(0,a.jsxs)(n.p,{children:["After, if is neccesary, you can use the fuctions ",(0,a.jsx)(n.code,{children:"cleaned_data "})," where you add the data, name of target column, name of location and date columns. For example:"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"data = cleaned_data(data,col_target='sessions',col_locations='location',col_dates='date')\n"})}),"\n",(0,a.jsx)(n.admonition,{type:"note",children:(0,a.jsx)(n.p,{children:"If you data have NaN values or the data is incomplete, this function is necessary to clean the data and not get errors."})}),"\n",(0,a.jsxs)(n.p,{children:["The function will clean the data of irregularities. After, you can ue the ",(0,a.jsx)(n.code,{children:"plot_geodata"})," function to see the data."]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"plot_geodata(data)\n"})}),"\n",(0,a.jsx)(n.h3,{id:"2-experimental-desing",children:"2. Experimental desing"}),"\n",(0,a.jsxs)(n.p,{children:["Now, you must configure the experimental design. In the ",(0,a.jsx)(n.code,{children:"run_geo_analysis"})," fuction must add the following parameters:"]}),"\n",(0,a.jsx)(n.p,{children:"The parameters needed to run this function are:"}),"\n",(0,a.jsxs)(n.ul,{children:["\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"data"}),": A data frame containing historical conversions by locations. This parameters must cotain a ",(0,a.jsx)(n.code,{children:"location"})," column, ",(0,a.jsx)(n.code,{children:"time"})," column and ",(0,a.jsx)(n.code,{children:"Y"})," column. That columns get after to run ",(0,a.jsx)(n.code,{children:"cleaned_fuction"})," or add the data manually with these feactures or the data must have this columns."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"excluded_states"}),": A list of states to exclude from treatment groups. These states will no be include in the treatment groups, but these can be include in the control groups."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"significance_level"}),": A number which is a significance level, that is mean, with ",(0,a.jsx)(n.code,{children:"significance_level=0.1"})," you have a 90% confidence level in your results."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"deltas_range"}),": This parameter contains a range of different lifts. You can agg the minimum lift, maximum lift and the steps. For example, if ",(0,a.jsx)(n.code,{children:"deltas_range = (0.01, 0.3, 0.02)"})," so the lifts will from 1% until 30% with 2% increments."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"periods_range"}),": A list constain a range of differents periods. This one is very parameter before. You can agg the minimum period, maximum period and the steps. For example, if ",(0,a.jsx)(n.code,{children:"periods_range = (5, 40, 5)"})," so the lifts will from 5 days until 40 days with 5 days of increments."]}),"\n"]}),"\n"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"geo_test = run_geo_analysis(\r\n    data = data,\r\n    excluded_states = ['mexico city', 'm\xe9xico'],\r\n    significance_level = 0.1,\r\n    deltas_range = (0.01, 0.3, 0.02),\r\n    periods_range = (5, 45, 5)\r\n)\r\n\n"})}),"\n",(0,a.jsx)(n.p,{children:"The results of the test provide us a visualization about the sensitivity in all periods admitted and differents holdouts. The holdouts depend of the data and locations, by default the number of treatment locations is 20% until 50% of total of locations. For example, if you have 32 locations, the range of size of treatment groups is 6-16 locations.\r\nWhe the simulation finish, you can see the heatmap of the results like this:"}),"\n",(0,a.jsx)(n.h3,{id:"3-results",children:"3. Results"}),"\n",(0,a.jsx)(n.p,{children:"Once the heatmap is displayed you can choose the best configuration for you, after that you can use the following functions to display the experiment results, such as the treatment and control locations, as well as metrics like MAE (Mean Absolute Error) and MAPE (Mean Absolute Percentage Error)."}),"\n",(0,a.jsx)(n.h4,{id:"treatment-and-control-groups",children:"Treatment and control groups"}),"\n",(0,a.jsxs)(n.p,{children:["For can get the treatment and control groups, you must run ",(0,a.jsx)(n.code,{children:"print_locations()"})," function, this one print the treatment and control group you choose. The parameters needed to run are:"]}),"\n",(0,a.jsxs)(n.ul,{children:["\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"geo_test"}),": Results of the main function (",(0,a.jsx)(n.code,{children:"run_geo_analysis"}),")."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"holdout_percentage"}),": The number of holdout percentage, this number you can see in the heatmap of the ",(0,a.jsx)(n.code,{children:"run_geo_analysis"})," function."]}),"\n"]}),"\n"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"print_locations(geo_test,holdout_percentage=85.75)\n"})}),"\n",(0,a.jsx)(n.h4,{id:"impact-graphs",children:"Impact graphs"}),"\n",(0,a.jsxs)(n.p,{children:["You can get a graph about lift, point difference and cumulative effect with the ",(0,a.jsx)(n.code,{children:"plot_impact_graphs()"})," function. The parameters for run are:"]}),"\n",(0,a.jsxs)(n.ul,{children:["\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"geo_test"}),": Results of the main function (",(0,a.jsx)(n.code,{children:"run_geo_analysis"}),")."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"period"}),": The period you want to see the impact graph."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"holdout_percentage"}),": The number of holdout percentage, this number you can see in the heatmap of the ",(0,a.jsx)(n.code,{children:"run_geo_analysis"})," function."]}),"\n"]}),"\n"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"plot_impact(geo_test,period=10,holdout_percentage=85.75)\n"})}),"\n",(0,a.jsx)(n.h4,{id:"weights",children:"Weights"}),"\n",(0,a.jsxs)(n.p,{children:["Murry can print the weights of the control locations that built the counterfactual, you just must run ",(0,a.jsx)(n.code,{children:"print_weighs()"}),". The parameters is the same that ",(0,a.jsx)(n.code,{children:"print_locations()"})," function. For example:"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"print_weights(geo_test,holdout_percentage=85.75)\n"})}),"\n",(0,a.jsx)(n.h3,{id:"incremental-results",children:"Incremental results"}),"\n",(0,a.jsxs)(n.p,{children:["You can get the incremental results with the ",(0,a.jsx)(n.code,{children:"plint_incremental_results()"})," function. The parameter is:"]}),"\n",(0,a.jsxs)(n.ul,{children:["\n",(0,a.jsxs)(n.li,{children:[(0,a.jsx)(n.code,{children:"geo_test"}),": Results of the main function (",(0,a.jsx)(n.code,{children:"run_geo_analysis"}),")."]}),"\n"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"print_incremental_results(geo_test)\n"})}),"\n",(0,a.jsx)(n.h3,{id:"metrics",children:"Metrics"}),"\n",(0,a.jsxs)(n.p,{children:["You can get the metrics of the experiment with the ",(0,a.jsx)(n.code,{children:"plot_metrics()"})," function. The parameter is:"]}),"\n",(0,a.jsxs)(n.ul,{children:["\n",(0,a.jsxs)(n.li,{children:[(0,a.jsx)(n.code,{children:"geo_test"}),": Results of the main function (",(0,a.jsx)(n.code,{children:"run_geo_analysis"}),")."]}),"\n"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"plot_metrics(geo_test)\n"})}),"\n",(0,a.jsx)(n.h2,{id:"experimental-evaluation",children:"Experimental Evaluation"}),"\n",(0,a.jsx)(n.h3,{id:"1-data",children:"1. Data"}),"\n",(0,a.jsx)(n.p,{children:"To evaluate an implemented experiment you can use Murray. This analysis is simpler than the design, but it is very similar in terms of functions and workflow. The first thing is to load read your data."}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:'data = pd.read_csv("data_marketing_campaign.csv")\n'})}),"\n",(0,a.jsx)(n.p,{children:"You can also use the same function to display the graph of the entered data."}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"plot_geodata(data)\n"})}),"\n",(0,a.jsx)(n.h3,{id:"2-experimental-evaluation",children:"2. Experimental evaluation"}),"\n",(0,a.jsxs)(n.p,{children:["This part is very similar to the experimental design, but in this case you must add the parameter to ",(0,a.jsx)(n.code,{children:"post_analysis"})," function. The parameters needed to run are:"]}),"\n",(0,a.jsxs)(n.ul,{children:["\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"data"}),": A data frame containing historical conversions by locations. This parameters must cotain a ",(0,a.jsx)(n.code,{children:"location"})," column, ",(0,a.jsx)(n.code,{children:"time"})," column and ",(0,a.jsx)(n.code,{children:"Y"})," column. That columns get after to run ",(0,a.jsx)(n.code,{children:"cleaned_fuction"})," or add the data manually with these feactures or the data must have this columns."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"start_treatment"}),": The start date of the treatment."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"end_treatment"}),": The end date of the treatment."]}),"\n"]}),"\n",(0,a.jsxs)(n.li,{children:["\n",(0,a.jsxs)(n.p,{children:[(0,a.jsx)(n.code,{children:"treatment_group"}),": The locations that are in the treatment group."]}),"\n"]}),"\n"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"results = post_analysis(data,start_treatment='2020-01-01',end_treatment='2020-01-31',treatment_group=['durango','puebla','queretaro'])\n"})}),"\n",(0,a.jsx)(n.h3,{id:"3-results-1",children:"3. Results"}),"\n",(0,a.jsx)(n.p,{children:"Once the post analysis is finished you can get the results with the following functions:"}),"\n",(0,a.jsx)(n.h4,{id:"impact-graph",children:"Impact graph"}),"\n",(0,a.jsxs)(n.p,{children:["You can get the impact graph with the ",(0,a.jsx)(n.code,{children:"plot_impact_graphs_evaluation()"})," function. The parameters are:"]}),"\n",(0,a.jsxs)(n.ul,{children:["\n",(0,a.jsxs)(n.li,{children:[(0,a.jsx)(n.code,{children:"results"}),": The results of the post analysis."]}),"\n"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"plot_impact_graphs_evaluation(results)\n"})}),"\n",(0,a.jsx)(n.h4,{id:"incremental-results-1",children:"Incremental results"}),"\n",(0,a.jsxs)(n.p,{children:["You can get the incremental results with the ",(0,a.jsx)(n.code,{children:"print_incremental_results_evaluation()"})," function. The parameters are:"]}),"\n",(0,a.jsxs)(n.ul,{children:["\n",(0,a.jsxs)(n.li,{children:[(0,a.jsx)(n.code,{children:"results"}),": The results of the post analysis."]}),"\n"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"print_incremental_results_evaluation(results)\n"})}),"\n",(0,a.jsx)(n.h4,{id:"permutation-test",children:"Permutation test"}),"\n",(0,a.jsxs)(n.p,{children:["You can get the permutation test with the ",(0,a.jsx)(n.code,{children:"plot_permutation_test()"})," function. The parameters are:"]}),"\n",(0,a.jsxs)(n.ul,{children:["\n",(0,a.jsxs)(n.li,{children:[(0,a.jsx)(n.code,{children:"results"}),": The results of the post analysis."]}),"\n"]}),"\n",(0,a.jsx)(n.pre,{children:(0,a.jsx)(n.code,{className:"language-python",children:"plot_permutation_test(results)\n"})})]})}function h(e={}){const{wrapper:n}={...(0,i.R)(),...e.components};return n?(0,a.jsx)(n,{...e,children:(0,a.jsx)(d,{...e})}):d(e)}},8453:(e,n,t)=>{t.d(n,{R:()=>r,x:()=>l});var s=t(6540);const a={},i=s.createContext(a);function r(e){const n=s.useContext(i);return s.useMemo((function(){return"function"==typeof e?e(n):{...n,...e}}),[n,e])}function l(e){let n;return n=e.disableParentContext?"function"==typeof e.components?e.components(a):e.components||a:r(e.components),s.createElement(i.Provider,{value:n},e.children)}}}]);
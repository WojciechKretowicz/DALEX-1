from warnings import warn
from plotly.subplots import make_subplots

from .checks import *
from .utils import calculate_ceteris_paribus, calculate_variable_split


class CeterisParibus:
    def __init__(self,
                 variables=None,
                 grid_points=101,
                 variable_splits=None):
        """Creates Ceteris Paribus object

        :param variables: variables for which the profiles are calculated
        :param grid_points: number of points in a single variable split if calculated automatically
        :param variable_splits: mapping of variables into points the profile will be calculated, if None then calculate with the function `_calculate_variable_splits`
        :return: None
        """

        self.variables = variables
        self.grid_points = grid_points
        self.variable_splits = variable_splits
        self.result = None
        self.new_observation = None

    def fit(self,
            explainer,
            new_observation,
            y=None):

        variables = check_variables(self.variables, explainer)
        data = check_data(explainer.data, variables)

        new_observation = check_new_observation(new_observation, explainer)

        if not check_variable_splits(self.variable_splits, variables):
            variable_splits = calculate_variable_split(data, variables, self.grid_points)

        y = check_y(y)

        self.result, self.new_observation = calculate_ceteris_paribus(explainer,
                                                                      new_observation,
                                                                      variable_splits,
                                                                      y)

    def plot(self, cp_list=None, size=2, color="#46bac2", variable_type="numerical", facet_ncol=2,
             variables=None, chart_title="Ceteris Paribus Profiles", show_observations=True,
             show_rugs=True):

        if variable_type not in ("both", "numerical", "categorical"):
            raise TypeError("variable_type should be 'both' or 'numerical' or 'categorical'")

        # are there any other explanations to plot?
        if cp_list is None:
            _result_df = self.result
            _obs_df = self.new_observation
        elif isinstance(cp_list, CeterisParibus):  # allow for list to be a single element
            _result_df = pd.concat([self.result, cp_list.result])
            _obs_df = pd.concat([self.new_observation, cp_list.new_observation])
        else:  # list as tuple or array
            _result_df = self.result
            _obs_df = self.new_observation
            for cp in cp_list:
                if not isinstance(cp, CeterisParibus):
                    raise TypeError("Some explanations aren't of CeterisParibus class")
                _result_df = pd.concat([_result_df, cp.result])
                _obs_df = pd.concat([_obs_df, cp.new_observation])

        # variables to use
        all_variables = _result_df['_vname_'].dropna().unique().tolist()

        if variables is not None:
            all_variables = np.intersect1d(all_variables, variables).tolist()
            if len(all_variables) == 0:
                raise TypeError("variables do not overlap with " + ''.join(variables))

        # names of numeric variables
        numeric_variables = _result_df[all_variables].select_dtypes(include=np.number).columns.tolist()

        if variable_type == "numerical":
            variable_names = numeric_variables

            if len(variable_names) == 0:
                # change to categorical
                variable_type = "categorical"
                # send message
                warn("'variable_type' changed to 'categorical' due to lack of numerical variables.")
                # take all
                variable_names = all_variables
            elif variables is not None and len(variable_names) != len(variables):
                raise TypeError("There are no numerical variables")
        else:
            variable_names = np.setdiff1d(all_variables, numeric_variables).tolist()

            # there are variables selected
            if variables is not None:
                # take all
                variable_names = all_variables
            elif len(variable_names) == 0:
                # there were no variables selected and there are no categorical variables
                raise TypeError("There are no non-numerical variables.")

        n = len(variable_names)

        # prepare clean observations data for tooltips
        m = _obs_df.shape[1]
        _obs_df.rename(columns={"_yhat_": "yhat", "_label_": "model", "_ids_": "id"}, inplace=True)
        _obs_df = _obs_df.iloc[:, np.concatenate(([m - 1, m - 2, m - 3], list(range(m - 3))))]  # reorder columns

        # split obs by id
        obs_df_list = [v for k, v in _obs_df.groupby('id', sort=False)]
        obs_df_dict = {e['id'].array[0]: e for e in obs_df_list}

        # prepare profiles data
        _result_df = _result_df.loc[_result_df['_vname_'].apply(lambda x: x in variable_names), ].reset_index(drop=True)

        dl = _result_df['_yhat_'].to_numpy()
        min_max = [np.Inf, -np.Inf]
        min_max_margin = dl.ptp() * 0.15
        min_max[0] = dl.min() - min_max_margin
        min_max[1] = dl.max() + min_max_margin

        # split var by variable
        var_df_list = [v for k, v in _result_df.groupby('_vname_', sort=False)]
        var_df_dict = {e['_vname_'].array[0]: e for e in var_df_list}

        facet_nrow = int(np.ceil(n / facet_ncol))
        fig = make_subplots(rows=facet_nrow, cols=facet_ncol, horizontal_spacing=0.1,
                            vertical_spacing=0.3/n, x_title='prediction', subplot_titles=variable_names)

        for i in range(n):
            name = variable_names[i]
            var_df = var_df_dict[name]

            row = int(np.floor(i/facet_ncol) + 1)
            col = int(np.mod(i, facet_ncol) + 1)

            # line plot or bar plot? TODO: add is_numeric and implement 'both'
            if variable_type == "numerical":
                ret = var_df[[name, "_yhat_", "_ids_", "_vname_"]].rename(
                    columns={name: "xhat", "_yhat_": "yhat", "_ids_": "id", "_vname_": "vname"})
                ret["xhat"] = pd.to_numeric(ret["xhat"])
                ret["yhat"] = pd.to_numeric(ret["yhat"])
                ret = ret.sort_values('xhat')

                df_list = [v for k, v in ret.groupby('id', sort=False)]

                for j in range(len(df_list)):
                    df = df_list[j]
                    obs = obs_df_dict[df.iloc[0, df.columns.get_loc('id')]].iloc[0, :]

                    tt = df.apply(lambda r: tooltip_text(obs, r), axis=1)
                    df = df.assign(tooltip_text=tt.values)

                    fig.add_scatter(
                        mode='lines',
                        y=df['yhat'].tolist(),
                        x=df['xhat'].tolist(),
                        line={'color': color, 'width': size, 'shape': 'spline'},
                        hovertext=df['tooltip_text'].tolist(),
                        hoverinfo='text',
                        hoverlabel={'bgcolor': 'rgba(0,0,0,0.8)'},
                        showlegend=False,
                        row=row, col=col
                    )

                    if show_observations:
                        fig.add_scatter(
                            mode='markers',
                            y=[obs.yhat],
                            x=[obs[name]],
                            marker={'color': '#371ea3', 'size': size*4},
                            hovertext=[tooltip_text(obs)],
                            hoverinfo='text',
                            hoverlabel={'bgcolor': 'rgba(0,0,0,0.8)'},
                            showlegend=False,
                            row=row, col=col)

                fig.update_yaxes({'type': 'linear', 'gridwidth': 2, 'zeroline': False, 'automargin': True,
                                  'ticks': 'outside', 'tickcolor': 'white', 'ticklen': 3, 'fixedrange': True},
                                 row=row, col=col)

                fig.update_xaxes({'type': 'linear', 'gridwidth': 2, 'zeroline': False, 'automargin': True,
                                  'ticks': "outside", 'tickcolor': 'white', 'ticklen': 3, 'fixedrange': True},
                                 row=row, col=col)

                fig.update_yaxes({'range': min_max})

            else:
                if _obs_df.shape[0] > 1:
                    raise TypeError("Please pick one observation.")

                ret = var_df[[name, "_yhat_", "_ids_", "_vname_"]].rename(
                    columns={name: "xhat", "_yhat_": "yhat", "_ids_": "id", "_vname_": "vname"})
                ret["yhat"] = pd.to_numeric(ret["yhat"])
                df = ret.sort_values('xhat')

                obs = obs_df_dict[df.iloc[0, df.columns.get_loc('id')]].iloc[0,:]
                baseline = obs.yhat

                difference = df['yhat'] - baseline
                df = df.assign(difference=difference.values)

                # lt = df.apply(lambda r: label_text(r), axis=1)
                # df = df.assign(label_text=lt.values)

                tt = df.apply(lambda r: tooltip_text(obs, r), axis=1)
                df = df.assign(tooltip_text=tt.values)

                fig.add_shape(type='line', x0=baseline, x1=baseline, y0=0, y1=len(df['xhat'].unique()) - 1, yref="paper", xref="x",
                              line={'color': "#371ea3", 'width': 1.5, 'dash': 'dot'}, row=row, col=col)

                fig.add_bar(
                    orientation="h",
                    y=df['xhat'].tolist(),
                    x=df['difference'].tolist(),
                    # textposition="outside",
                    # text=df['label_text'].tolist(),
                    marker_color=color,
                    base=baseline,
                    hovertext=df['tooltip_text'].tolist(),
                    hoverinfo='text',
                    hoverlabel={'bgcolor': 'rgba(0,0,0,0.8)'},
                    showlegend=False,
                    row=row, col=col)

                fig.update_yaxes({'type': 'category', 'autorange': 'reversed', 'gridwidth': 2, 'automargin': True,
                                  'ticks': 'outside', 'tickcolor': 'white', 'ticklen': 10, 'fixedrange': True},
                                 row=row, col=col)

                fig.update_xaxes({'type': 'linear', 'gridwidth': 2, 'zeroline': False, 'automargin': True,
                                  'ticks': "outside", 'tickcolor': 'white', 'ticklen': 3, 'fixedrange': True},
                                 row=row, col=col)

                fig.update_xaxes({'range': min_max})

        plot_height = 78 + 71 + facet_nrow*(280+60)
        fig.update_layout(title_text=chart_title, title_x=0.15, font={'color': "#371ea3"}, template="none",
                          height=plot_height, margin={'t': 78, 'b': 71, 'r': 30}, hovermode='closest')

        fig.show(config={'displaylogo': False, 'staticPlot': False,
            'modeBarButtonsToRemove': ['sendDataToCloud', 'lasso2d', 'autoScale2d', 'select2d', 'zoom2d', 'pan2d',
                                       'zoomIn2d', 'zoomOut2d', 'resetScale2d', 'toggleSpikelines', 'hoverCompareCartesian',
                                       'hoverClosestCartesian']})


def tooltip_text(obs, r=None):
    temp = ""
    if r is not None:
        for var in obs.index:
            if var == "yhat":
                temp += "prediction:<br>" + "- before: " + str(obs[var]) + "<br>" + "- after: " +\
                        str(r.yhat) + "<br><br>"
            elif var == r.vname:
                temp += var + ": " + str(r.xhat) + "</br>"
            else:
                temp += var + ": " + str(obs[var]) + "</br>"
    else:
        for var in obs.index:
            if var == "yhat":
                temp += "prediction:" + str(obs[var]) + "<br>"
            else:
                temp += var + ": " + str(obs[var]) + "</br>"
    return temp


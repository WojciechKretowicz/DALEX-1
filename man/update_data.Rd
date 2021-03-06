% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/misc_update.R
\name{update_data}
\alias{update_data}
\title{Update data of an explainer object}
\usage{
update_data(explainer, data, y = NULL, verbose = TRUE)
}
\arguments{
\item{explainer}{- explainer object that is supposed to be updated.}

\item{data}{- new data, is going to be passed to an explainer}

\item{y}{- new y, is going to be passed to an explainer}

\item{verbose}{- logical, indicates if information about update should be printed}
}
\value{
updated explainer object
}
\description{
Function allows users to update data an y of any explainer in a unified way. It doesn't require knowledge about structre of an explainer.
}
\examples{
aps_lm_model4 <- lm(m2.price ~., data = apartments)
aps_lm_explainer4 <- explain(aps_lm_model4, data = apartments, label = "model_4v")
explainer <- update_data(aps_lm_explainer4, data = apartmentsTest, y = apartmentsTest$m2.price)

}

# Implementing Model Checks

> by Christoph A. Johns (christoph.johns@aalto.fi)

In the following, I document the process of implementing several helper functions to develop tasks and operators using the `interactionagents` package.

## Potential Features

Following features or functions could be useful when developing a computational interaction experiment and could be explored:

- [ ] Parameter recovery (correlation, Pearson's r)
- [ ] Model recovery (confusion matrix, recall, precision, F-score)
- [ ] Posterior predictive checking
- [ ] Identifiability (reasonable parameter fit bounds)
- [ ] Task richness (quality of parameter and model recovery dependent on task parameters)
- [ ] Behavior visualization
- [ ] Exploratory simulations (isolating parameter effects)
- [ ] Correlations between recovered parameters
- [ ] Quality of simulated data from recovered models

## Development Process

Over the course of my internship from August until November 2021, I have developed the above features using the following process:

### Parameter and Model Recovery

Following the [tutorial on user modeling by Aurélien Nioche](https://nbviewer.jupyter.org/github/AurelienNioche/LectureUserResearch/blob/master/lecture10.ipynb), I iterated over five versions of the parameter and model recovery he outlined, each time increasing the complexity and similarity of my implementation to the structure of the `interactionagents` package.
The example task and models I used to test and develop my functions were the Multi Bandit task and the Random Operator, Win-Stay-Lose-Switch and Rescorla-Wagner models described in the tutorial.

The **first iteration** simply abstracted the plots and calculations he provided into separate functions for increased ease of use.

The **second iteration** introduced a simplified `Task` and `Model` class each to attempt and abstract away their parameters from the parameter and model recovery functions.
At this point in time, I assumed that both the parameter and model recovery functions would function as assertions or tests that could included in a test case or test suite by the researcher.
While implementing the functions and reading additional literature (e.g. [1], [2]), however, it became clear that exploring the behavior visually was much more relevant to users than simple assertions that do not provide further insight.

For the **third iteration**, I created a mock version of the `interactionagents` package that included simplified versions of the relevant `BaseAgent`, `InteractionTask`, `Bundle` and `ELLDiscretePolicy` classes.
On their basis, I recreated or adapted the previous functions for parameter and model recovery to work with the relevant class structure.

For the **fourth iteration**, I implemented the example task and models using the current version of the `interactionagents` package and introduced a new `modeling` subpackage with a `modeling.parameter_recovery` and `modeling.model_recovery` module respectively that bundled the previously introduced functions for improved ease of use.
I further adapted the functions where required to work with the actual format required by the `interactionagents` package.

The **fifth iteration** moved the contents of the previously introduced `modeling` subpackage into a new helper class called `DevelopOperator` that could be used to explore behavior of operator agents when designing a computational interaction experiment without requiring the implementation of an assistant or the specification of the operators hyperparameter values.

---

#### References

[1] R. C. Wilson and A. G. Collins, “Ten simple rules for the computational modeling of behavioral data,” eLife, vol. 8, p. e49547, Nov. 2019, doi: 10.7554/eLife.49547.

[2] A. Heathcote, S. D. Brown, and E.-J. Wagenmakers, “An Introduction to Good Practices in Cognitive Modeling,” in An Introduction to Model-Based Cognitive Neuroscience, B. U. Forstmann and E.-J. Wagenmakers, Eds. New York, NY: Springer New York, 2015, pp. 25–48. doi: 10.1007/978-1-4939-2236-9_2.

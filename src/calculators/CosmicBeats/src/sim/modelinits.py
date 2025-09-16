"""
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty Created on: 31 Oct 2022 @desc In this module, we list the initialization methods for
different model class implementations. Initialization method must be written in the same module as where class
implementation is written. The initialization method must be added in the dictionary below as the value against the
key as the name of the class The prototype of the initialization method goes below.

    init_Classname(_ownernodeins:INode, _loggerins:ILogger, _modelArgs) -> IModel
    Here,
    @desc
        This method initializes an instance of ModelOrbit class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info.
        The JSON object must have the literals as follows (values are given as example).
        {
            "tle_1": "1 50985U 22002B   22290.71715197  .00032099  00000+0  13424-2 0  9994",
            "tle_2": "2 50985  97.4784 357.5505 0011839 353.6613   6.4472 15.23462773 42039",
        }
    @return
        Instance of the model class
"""

# import the node class here
from ..models.models_orbital.modelorbit import init_ModelOrbit
from ..models.models_orbital.modelorbitonefullupdate import init_ModelOrbitOneFullUpdate
from ..models.models_orbital.modelfixedorbit import init_ModelFixedOrbit

from ..models.models_fov.modelhelperfov import init_ModelHelperFoV
from ..models.models_fov.modelfovtimebased import init_ModelFovTimeBased

modelInitDictionary = {
    "ModelOrbit": init_ModelOrbit,
    "ModelOrbitOneFullUpdate": init_ModelOrbitOneFullUpdate,
    "ModelFixedOrbit": init_ModelFixedOrbit,
    
    "ModelHelperFoV": init_ModelHelperFoV,
    "ModelFovTimeBased": init_ModelFovTimeBased
    }

from pkg_resources import Requirement
from pkg_resources import working_set
__version__ = working_set.find(Requirement.parse('pmr2.wfctrl')).version

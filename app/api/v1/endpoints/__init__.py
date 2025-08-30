from .auth import router as auth
from .content import router as content
from .gamification import router as gamification
from .groups import router as groups
from .learning import router as learning
from .learning_centers import router as learning_centers
from .users import router as users

__all__ = ['auth','content','gamification','groups','learning','learning_centers','users']

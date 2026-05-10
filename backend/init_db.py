from database import engine, Base
from models import (
    School,
    User,
    Class,
    Survey,
    SurveyResponse,
    SurveyAnswer,
    ClassModel,
    LoginAttempt,
)


def main():
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


if __name__ == "__main__":
    main()

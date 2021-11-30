FROM python:3.10

WORKDIR /app
COPY ./requirements.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install -U pip setuptools wheel
RUN pip install -r requirements.txt && python -m spacy download en_core_web_sm
COPY . .
CMD python -u tg_bot.py
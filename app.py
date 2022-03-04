from flask import Flask, jsonify, make_response, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, ForeignKey, true
from flask_restful import Api, Resource
from flask_cors import CORS
from sqlalchemy.orm import backref
from datetime import date
import os
from functools import wraps
from ibm_watson import SpeechToTextV1, LanguageTranslatorV3, NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson.natural_language_understanding_v1 import Features, EmotionOptions



pv_key = 'NTNv7j0TuYARvmNMmWXo6fKvM4o6nv/aUi9ryX38ZH+L1bkrnD1ObOQ8JAUmHCBq7Iy7otZcyAagBLHVKvvYaIpmMuxmARQ97jUVG16Jkpkp1wXOPsrF9zwew6TpczyHkHgX5EuLg2MeBuiT/qJACs1J0apruOOJCg/gOtkjB4c='

apikey = 'Q9vpRxHigLR4nl8fY8Gg6zUUoPD8CXwAtX77LlQWNlVx'
url = 'https://api.eu-gb.speech-to-text.watson.cloud.ibm.com/instances/6b2ddda5-da72-405d-85bb-dd2be4856764'
authenticator = IAMAuthenticator(apikey)
stt = SpeechToTextV1(authenticator=authenticator)
stt.set_service_url(url)


nlApiKey = 'Qjjas6sAJikcL0DaFy9ANwDoX3VUcFGjiqa3vEpMVOEr'
nlURL = 'https://api.eu-gb.natural-language-understanding.watson.cloud.ibm.com/instances/3d64cf36-1adf-4e17-a414-715903062fe2'
nlAuthenticator = IAMAuthenticator(nlApiKey)
nlu = NaturalLanguageUnderstandingV1(version='2021-08-01', authenticator=nlAuthenticator)
nlu.set_service_url(nlURL)

tAuthenticator = IAMAuthenticator('bQVKAr9KIzioDei0B3I__3OxxzyCxLum_39aw5sPuq0l')
translator = LanguageTranslatorV3(version='2018-05-01', authenticator=tAuthenticator)
translator.set_service_url('https://api.eu-gb.language-translator.watson.cloud.ibm.com/instances/a05d8392-e42d-4d75-a999-68f10ec1d2cc')

app = Flask(__name__)
CORS(app)

cors = CORS(app, resource={
    r"/*" : {
        "origins" : "*"
    }
})
api = Api(app)

app.config['SECRET_KEY'] = pv_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.curdir , 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.config['MAX_CONTENT_PATH'] = 2 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/uploads'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg', 'm4a'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Movie(db.Model):
    __tablename__ = 'Movie'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    poster = Column(String())
    director = Column(String(100))

class Comment(db.Model):
    __tablename__ = 'Comment'
    id = Column(Integer, primary_key=True)
    comment = Column(String(1000), nullable=False)
    username = Column(String(100), nullable=False)
    movieId = Column(Integer, ForeignKey('Movie.id'), nullable=False)
    movie = db.relationship("Movie", backref=backref("Movie", uselist=False))


@app.route('/movies', methods=['GET'])
def getMovies():
    movies = Movie.query.all()
    return jsonify([{
        'id': movie.id,
        'name': movie.name,
        'poster': movie.poster,
        'director': movie.director
    } for movie in movies])

@app.route('/uploadVoiceFile/<movie_id>', methods=['POST'])
def uploadFile(movie_id):
    try:
        id = movie_id
        print(id)
    except Exception as ex:
        return 'Issue in getting movieId'
    
    voice_file = request.files['file']
    print(voice_file)
    print(voice_file.filename.rsplit('.', 1)[1].lower())
    if voice_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
        translateCM = stt.recognize(audio=voice_file, content_type='application/octet-stream',model='en-US_BroadbandModel').get_result()
        print(translateCM)
        if len(translateCM['results']) != 0:
            comment = translateCM['results'][0]['alternatives'][0]['transcript']
        else:
            return jsonify({'value':'No voice detected'})
        res = nlu.analyze(text=comment,features=Features(emotion=EmotionOptions())).get_result()['emotion']['document']['emotion']['anger']
        print(res)
        if res > 0.5:
            return jsonify({'value':'Bad words in file.'})
        else:
            newCm = Comment(comment=comment, username='sadra', movieId=id)
            db.session.add(newCm)
            db.session.commit()
            return jsonify({'value':'Comment added successfully!'})


@app.route('/getComments/<movie_id>', methods=['GET'])
def get_comments(movie_id):
    try:
        lang = request.args.get('lang')
    except Exception as ex:
        lang = 'en'
    
    
    if lang is None:
        lang = 'en'

    movieCms = Comment.query.filter(Comment.movieId == movie_id)
    if lang != 'en':
        for cm in movieCms:
            cm.comment = translator.translate(text=cm.comment, model_id='en-' + lang).get_result()['translations'][0]['translation']

    
    return jsonify([{
        'comment' : cm.comment,
        'username': cm.username,
        'id': cm.id
    } for cm in movieCms])
    



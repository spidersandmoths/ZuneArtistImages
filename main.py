from flask import Flask, send_file, Response, abort, make_response
import pylast
import cv2
import requests  
import html
from pathlib import Path
from datetime import datetime, timedelta, date
import os
import threading
import os.path
from time import sleep, time
import musicbrainzngs
import discogs_client
from google_images_search import GoogleImagesSearch


cwd = os.getcwd() 
app = Flask(__name__)
gis = GoogleImagesSearch('key here', 'project cx here')
d = discogs_client.Client('Zune Artist Images Recreation Server/1.1', user_token="discogs token here")
musicbrainzngs.set_useragent("Zune artist images recreation server", "1.1", "cobboskar9@gmail.com")
API_KEY = "last.fm key here"
API_SECRET = "last.fm secret here"
username = "last.fm username here"
password_hash = pylast.md5("last.fm password here")
network = pylast.LastFMNetwork(
    api_key=API_KEY,
    api_secret=API_SECRET,
    username=username,
    password_hash=password_hash,
)
headers = {
    'User-Agent': 'Zune Artist Images Recreation Server/1.1',
    'From': 'cobboskar9@gmail.com'
}


class discogsID:
    def __init__(self):
        pass

    def get(mbid):
        urlList = musicbrainzngs.get_artist_by_id(mbid, includes="url-rels")["artist"]["url-relation-list"]
        for num, value in enumerate(urlList):
            if urlList[num]["type"] == "discogs":
                id = urlList[num]["target"].split("/")[-1]
        return id
    
    def getMBID(id):
        return musicbrainzngs.browse_urls(f"https://www.discogs.com/artist/{str(int(id))}", includes=["artist-rels"])["url"]["artist-relation-list"][0]["artist"]["id"]
    
    def getUUID(mbid):
        zeros = ""
        dcid = discogsID.get(mbid)
        for i in range(1, 9 - len(dcid)):
            zeros = zeros + "0"
        return zeros + dcid + "-6000-0000-0000-000000000000"


def getArtist(mbid):
    try:
        return network.get_artist_by_mbid(mbid)
      
    except pylast.WSError:
        urlList = musicbrainzngs.get_artist_by_id(mbid, includes="url-rels")["artist"]["url-relation-list"]
        for num, value in enumerate(urlList):
            if urlList[num]["type"] == "last.fm":
                name = urlList[num]["target"].split("/")[-1]
                return network.get_artist(name.replace("+", " "))     


def cropImg(image):
    #Load image
    img = cv2.imread(image)

    #Set aspect ratio
    original_height, original_width = img.shape[:2]
    
    #Define new width while maintaining the aspect ratio
    new_width = 480
    aspect_ratio = new_width / original_width
    new_height = int(original_height * aspect_ratio)

    #Crop image
    cropped_image = cv2.resize(img, (new_width, new_height))

    #Save image
    cv2.imwrite(image, cropped_image)


def cropThumb(image):
    #Load image
    img = cv2.imread(image)

    original_height, original_width = img.shape[:2]

    #Define new width while maintaining the aspect ratio
    new_width = 160
    aspect_ratio = new_width / original_width
    new_height = int(original_height * aspect_ratio)

    #Crop image
    cropped_image = cv2.resize(img, (new_width, new_height))

    #Define the region of interest (ROI) - arbitrary coordinates
    x_start = int((int(cropped_image.shape[1]) / 2) - 80)
    y_start = 0
    x_end = int((int(cropped_image.shape[1]) / 2) + 80) 
    y_end = 120

    #Crop the image using slicing
    cropped_img = cropped_image[y_start:y_end, x_start:x_end]

    cv2.imwrite(image, cropped_img)


#I forgot what this did
def getData(url):  
    r = requests.get(url)  
    return r.text  


def writeImages(artist, imgNum, data):
    if imgNum == 0: 
        with open(f'artists/{artist}/thumb.jpg','wb') as f:
            f.write(data)
            cropThumb(f"artists/{str(artist).replace("/", "-")}/thumb.jpg")
    else:
        with open(f'artists/{artist}/{imgNum}.jpg','wb') as f:
            f.write(data)
            cropImg(f"artists/{str(artist).replace("/", "-")}/{imgNum}.jpg")


def getImages(dcid):
    imgData = []
    imgNum = 0

    print("test")

    artist = d.artist(dcid)

    #Get all images at once and store the data in a list
    while imgNum < 8:
        try:
            imgData.append(requests.get(artist.images[imgNum]["resource_url"], allow_redirects=True, headers=headers).content)
            print("done")
            imgNum = imgNum + 1
        except IndexError:
            gis.search(search_params={
                'q': f'"{artist.name}" band -"ai" -amazon -ebay -etsy -"merch" -album -"interview" -"stock photos" -"for sale" -"youtube" -"shopify"', 
                'num': 8 - imgNum, 
                'fileType': 'jpg'})
            for image in gis.results():
                imgData.append(requests.get(image.url).content)
                print("done")
            imgNum = 8


    sleep(1)

    for i in range(0, imgNum):
        try:
            writeImages(str(getArtist(discogsID.getMBID(dcid))).replace("/", "-"), i, imgData[i])
        except AttributeError:
            if i == 0:
                print(f"Error: Thumbnail image could not be written properly, removing file.")
                os.remove(f"artists/{str(getArtist(discogsID.getMBID(dcid))).replace("/", "-")}/thumb.jpg")
            else:
                print(f"Error: Image {i} could not be written properly, removing file.")
                os.remove(f"artists/{str(getArtist(discogsID.getMBID(dcid))).replace("/", "-")}/{i}.jpg")


@app.route("/v3.0/en-US/music/artist/<mbid>", strict_slashes=False)
def overview(mbid):
    imgID = discogsID.getUUID(mbid)
    artist = getArtist(mbid)

    try:
        Path(f"artists/{str(artist).replace("/", "-")}").mkdir()
        print(f"Directory created successfully.")
    except FileExistsError:
        print(f"Directory already exists.")
    except PermissionError:
        print(f"Permission denied: Unable to create dir.")
        return "500 Internal Server Error", 500
    except Exception as e:
        print(f"An error occurred: {e}")
        return "500 Internal Server Error", 500

    #check the last time images were grabbed and determine if they need to be updated
    with open(f"artists/{str(artist).replace("/", "-")}/lastUpdated.txt", "w+") as prevDate:
        try:
            if (date.today() - timedelta(7)) >= datetime.strptime(prevDate.readline(), "%Y-%m-%d").date():
                prevDate.write(str(date.today()))
                threading.Thread(target = getImages, args = [discogsID.get(mbid)]).start()
        except ValueError:
            prevDate.write(str(date.today()))
            threading.Thread(target = getImages, args = [discogsID.get(mbid)]).start()

    xmlData = f'<?xml version="1.0" encoding="utf-8"?><a:entry xmlns:a="http://www.w3.org/2005/Atom" xmlns:os="http://a9.com/-/spec/opensearch/1.1/" xmlns="http://schemas.zune.net/catalog/music/2007/10"><a:link rel="zune://artist/biography" type="application/atom+xml" href="/v3.0/en-US/music/artist/{mbid}/biography" /><a:link rel="self" type="application/atom+xml" href="/v3.0/en-US/music/artist/{mbid}" /><a:updated>1900-01-01T00:00:00.000000Z</a:updated><a:title type="text">{artist}</a:title><a:id>urn:uuid:{mbid}</a:id><sortName>{artist}</sortName><playRank>0</playRank><playCount>0</playCount><favoriteCount>0</favoriteCount><sendCount>0</sendCount><isDisabled>False</isDisabled><startDate>1900-01-01T00:00:00Z</startDate><image><id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0010", 1)}</id></image><a:author><a:name>Microsoft Corporation</a:name></a:author></a:entry>' + "\n\n\n\n\n\n\n "
    
    return Response(xmlData, mimetype='application/xml', headers={
            'Content-Type': 'application/xml',
            'Cache-Control': 'max-age=86400',
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=150000, max=10',
            'Expires': 'Sun, 19 Apr 2071 10:00:00 GMT',
            'Access-Control-Allow-Origin': '*'
        })


@app.route("/v3.0/en-US/music/artist/<mbid>/deviceBackgroundImage", strict_slashes=False)
def backgroundImage(mbid):
    artist = getArtist(mbid)

    while os.path.isfile(f"artists/{str(artist).replace("/", "-")}/7.jpg") == False:
        sleep(0.5)
    return send_file(f"artists/{str(artist).replace("/", "-")}/7.jpg", mimetype="image/jpeg") 


@app.route("/v3.0/en-US/image/<imgID>/", strict_slashes=False)
def getImg(imgID):
    headers={
            'Content-Type': 'image/jpeg',
            'Cache-Control': 'max-age=86400',
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=150000, max=10',
            'Expires': 'Sun, 19 Apr 2071 10:00:00 GMT',
            'Access-Control-Allow-Origin': '*'
        }
    
    try:
        mbid = discogsID.getMBID(imgID.split("-")[0])
    except ValueError:
        return abort(404)
    artist = getArtist(mbid)

    sleep(0.5)
    if os.path.isdir(f"artists/{str(artist).replace("/", "-")}") == False:
        sleep(1)
        if os.path.isdir(f"artists/{str(artist).replace("/", "-")}") == False:
            try:
                Path(f"artists/{str(artist).replace("/", "-")}").mkdir()
                print(f"Directory created successfully.")
            except FileExistsError:
                print(f"Directory already exists.")
            except PermissionError:
                print(f"Permission denied: Unable to create dir.")
                return "500 Internal Server Error", 500
            except Exception as e:
                print(f"An error occurred: {e}")
                return "500 Internal Server Error", 500
            threading.Thread(target = getImages, args = [discogsID.get(mbid)]).start()

    if int(imgID.split("-")[1]) in range(1,7) or int(imgID.split("-")[1]) == 10:
        num = int(imgID.split("-")[1])
    else:
        return abort(404)

    startTime = time()
    while (os.path.isfile(f"artists/{str(artist).replace("/", "-")}/{num}.jpg") == False and num != 10) or os.path.isfile(f"artists/{str(artist).replace("/", "-")}/thumb.jpg") == False:
        sleep(0.5)
        if (time() - startTime) > 6:
            print("timeout")
            return abort(404)


    if num == 10:
        response = make_response(send_file(f"artists/{str(artist).replace("/", "-")}/thumb.jpg", mimetype="image/jpeg"))
    else:
        response = make_response(send_file(f"artists/{str(artist).replace("/", "-")}/{num}.jpg", mimetype="image/jpeg"))

    response.headers = headers
    return response


@app.route("/v3.0/en-US/music/artist/<mbid>/albums", strict_slashes=False)
def albums(mbid):
    artist = getArtist(mbid)
    return artist


@app.route("/v3.0/en-US/music/artist/<mbid>/similarArtists", strict_slashes=False)
def similar(mbid):
    artist = getArtist(mbid)
    return artist


@app.route("/v3.0/en-US/music/artist/<mbid>/tracks", strict_slashes=False)
def tracks(mbid):
    artist = getArtist(mbid)
    return artist


@app.route("/v3.0/en-US/music/artist/<mbid>/biography", strict_slashes=False)
def bio(mbid):
    artist = getArtist(mbid)
    bio = artist.get_bio("content")
    xmlData = f'<?xml version="1.0" encoding="utf-8"?><a:entry xmlns:a="http://www.w3.org/2005/Atom" xmlns:os="http://a9.com/-/spec/opensearch/1.1/" xmlns="http://schemas.zune.net/catalog/music/2007/10"><a:link rel="self" type="application/atom+xml" href="/v3.0/en-US/music/artist/f46bd570-5768-462e-b84c-c7c993bbf47e/biography" /><a:updated>1900-01-01T00:00:00.0000000Z</a:updated><a:title type="text">{artist}</a:title><a:id>tag:catalog.zune.net,1900-01-01:/music/artist/{mbid}/biography</a:id><a:content type="html">{html.escape(bio)}</a:content><a:author><a:name>Microsoft Corporation</a:name></a:author></a:entry>'
    return Response(xmlData, mimetype='application/xml', headers={
            'Content-Type': 'application/xml',
            'Cache-Control': 'max-age=86400',
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=150000, max=10',
            'Expires': 'Sun, 19 Apr 2071 10:00:00 GMT',
            'Access-Control-Allow-Origin': '*'
        })


@app.route("/v3.0/en-US/music/artist/<mbid>/images", strict_slashes=False)
def images(mbid):
    #shortid = shortuuid.encode(UUID(mbid))
    #imgID = f"000000{shortid[:2]}-0000-{shortid[2:6]}-{shortid[6:10]}-{shortid[10:]}"
    imgID = discogsID.getUUID(mbid)
    artist = getArtist(mbid)

    xmlData = f'<?xml version="1.0" encoding="utf-8"?><a:feed xmlns:a="http://www.w3.org/2005/Atom" xmlns:os="http://a9.com/-/spec/opensearch/1.1/" xmlns="http://schemas.zune.net/catalog/music/2007/10"><a:link rel="self" type="application/atom+xml" href="/v3.0/en-US/music/artist/{mbid}/images" /><a:updated>1900-01-01T00:00:00.000000Z</a:updated><a:title type="text">List Of Items</a:title><a:id>tag:catalog.zune.net,1966-09-20:/music/artist/{mbid}/images</a:id><a:entry><a:updated>1900-01-01T00:00:00.000000Z</a:updated><a:title type="text">List Of Items</a:title><a:id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0001", 1)}</a:id><instances><imageInstance><id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0001", 1)}</id><url>http://art.zune.net/1/{imgID.replace(imgID.split("-")[1], "0001", 1)}/504/image.jpg</url><format>jpg</format><width>1000</width><height>1000</height></imageInstance></instances></a:entry><a:entry><a:updated>1900-01-01T00:00:00.000000Z</a:updated><a:title type="text">List Of Items</a:title><a:id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0002", 1)}</a:id><instances><imageInstance><id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0002", 1)}</id><url>http://art.zune.net/1/{imgID.replace(imgID.split("-")[1], "0002", 1)}/504/image.jpg</url><format>jpg</format><width>1000</width><height>1000</height></imageInstance></instances></a:entry><a:entry><a:updated>1900-01-01T00:00:00.000000Z</a:updated><a:title type="text">List Of Items</a:title><a:id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0003", 1)}</a:id><instances><imageInstance><id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0003", 1)}</id><url>http://art.zune.net/1/{imgID.replace(imgID.split("-")[1], "0003", 1)}/504/image.jpg</url><format>jpg</format><width>1000</width><height>1000</height></imageInstance></instances></a:entry><a:entry><a:updated>1900-01-01T00:00:00.000000Z</a:updated><a:title type="text">List Of Items</a:title><a:id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0004", 1)}</a:id><instances><imageInstance><id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0004", 1)}</id><url>http://art.zune.net/1/{imgID.replace(imgID.split("-")[1], "0004", 1)}/504/image.jpg</url><format>jpg</format><width>1000</width><height>1000</height></imageInstance></instances></a:entry><a:entry><a:updated>1900-01-01T00:00:00.000000Z</a:updated><a:title type="text">List Of Items</a:title><a:id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0005", 1)}</a:id><instances><imageInstance><id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0005", 1)}</id><url>http://art.zune.net/1/{imgID.replace(imgID.split("-")[1], "0005", 1)}/504/image.jpg</url><format>jpg</format><width>1000</width><height>1000</height></imageInstance></instances></a:entry><a:entry><a:updated>1900-01-01T00:00:00.000000Z</a:updated><a:title type="text">List Of Items</a:title><a:id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0006", 1)}</a:id><instances><imageInstance><id>urn:uuid:{imgID.replace(imgID.split("-")[1], "0006", 1)}</id><url>http://art.zune.net/1/{imgID.replace(imgID.split("-")[1], "0006", 1)}/504/image.jpg</url><format>jpg</format><width>1000</width><height>1000</height></imageInstance></instances></a:entry><a:author><a:name>Microsoft Corporation</a:name></a:author></a:feed>'
    return Response(xmlData, mimetype='application/xml', headers={
            'Content-Type': 'application/xml',
            'Cache-Control': 'max-age=86400',
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=150000, max=10',
            'Expires': 'Sun, 19 Apr 2071 10:00:00 GMT',
            'Access-Control-Allow-Origin': '*'
        })


if __name__ == '__main__':
    print("Checking if ./artists/ exists")

    try:
        Path("artists").mkdir()
        print("Directory ./artists/ created successfully.")
    except FileExistsError:
        print("Directory ./artists/ already exists.")
    except PermissionError:
        print("Permission denied: Unable to create directory ./artists/")
        exit()
    except Exception as e:
        print(f"An error occurred: {e}")
        exit()
    app.run(host="127.0.0.2", port=80)
else:
    print("Checking if ./artists/ exists")

    try:
        Path("artists").mkdir()
        print("Directory ./artists/ created successfully.")
    except FileExistsError:
        print("Directory ./artists/ already exists.")
    except PermissionError:
        print("Permission denied: Unable to create directory ./artists/")
        exit()
    except Exception as e:
        print(f"An error occurred: {e}")
        exit()


# ZuneArtistImages
Zune.net server recreation for the background artist images on the Zune HD
## Using the server and Zune setup
Before starting please ensure that either the "MusicBrainz ID Locator" mod has been applied to your music library via the [Zune Modding Helper](https://github.com/ZuneDev/ZuneModdingHelper), or you have set the ZUNEALBUMARTISTMEDIAID metadata tag your library with the value set to the corresponding track artist.

Once your library has been properly set with either the metadata tag manually, or the modding helper automatically, you must append and save the following lines to the windows hosts file:
```
YOUR IP catalog.zune.net
YOUR IP image.catalog.zune.net
YOUR IP mix.zune.net
```
Note: you must ***not*** change "YOUR IP" to 127.0.0.1 or localhost, as in testing it would not work. Please instead change it to the ip given to you by your router.

Setting this in the hosts file is important due to the zune player going through your pc to access the zune servers while plugged in. Changing these values allows the Zune to see this server instead of zune.net while plugged in.

Once these steps have been completed, please delete all music and other content attached to the artist or artists you plan to use this server with from the Zune player. This is a one-time step, as after music that has been properly set with either the metadata or modding helper methods has been synced, theZzune will automatically reach out to try and get info for them. If you have music synced that has been set up with either method already on the player, you will not have to delete it from the device.

After it finishes, sync all of the newly tagged/modded music back on to the Zune player and wait fully for it to say sync complete before removing the device.


## Server setup
This server is intended to be run with Nginx acting as a reverse proxy.

To start the servers, please boot up the server with Gunicorn:

```sudo your/path/to/gunicorn main:app```

The configuration file included in this repository should be seen automatically by Gunicorn, however if it isn't you may need to append 
``` -c gunicorn.conf.py``` to the end of the command above. 

When configuring Nginx, please ensure the following domains are listed in the reverse proxy configuration:
```
catalog.zune.net
image.catalog.zune.net
mix.zune.net
```

These need to be redirected to the server, which should be running at http://127.0.0.1:8000.


## Troubleshooting
If you find the images are not present, or only some images are there, please do the following steps:

1. Close the zune software
2. Fully power down the Zune player
3. Make sure the cable is connected
4. Power the zune back on

After a few seconds, the Zune should boot back up and the desktop software should autolaunch. Please give the Zune between 30 seconds to 1 minute to sit and talk to the server before unplugging again or closing the software. The Zune may be talking to the server even when giving no indication.

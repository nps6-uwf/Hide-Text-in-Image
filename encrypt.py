'''
Hide Image in Text
Author: Nick Sebasco
Date: 1/10/2022
'''


from cryptography.fernet import Fernet
from PIL import Image
import piexif
import pickle
from itertools import product
from random import sample, randint
import numpy as np
from sys import argv, exit
import os.path
import argparse


parser = argparse.ArgumentParser()
# If this argument is present the program will run in encryption mode
parser.add_argument('-write', action='store_true')
# input file name
parser.add_argument('-i','--input', type=str, nargs='?', default="'testImages/monkey.png'")
# output file name
parser.add_argument('-o', '--output', type=str, nargs='?', default='image.png')
args = parser.parse_args()


def encryption(msg: str, saveToPickle: bool = True) -> tuple:
    ''' encrypt a message and return the encrypted text along with the fernet instance
    which can be used to decrypt.
    '''
    key = Fernet.generate_key()
    fernet = Fernet(key)
    
    if saveToPickle:
        with open("key.pickle","wb") as p:
            pickle.dump(fernet,p)

    return (fernet.encrypt(msg.encode()), fernet)


def getUserInput() -> str:
    ''' Generate menu for program when user enters in encryption mode.
    '''
    while True:
        try: 
            option = int(input("\n".join([
                        "How would you like to embed the secret message into the image?",   
                        "[1] manual input",
                        "[2] text file",
                        "[3] exit\n"])).strip())
            if option == 1:
                return input("Enter your secret message: ")
            elif option == 2:
                with open(input("Enter text file path: "), "r") as f:
                    return f.read()
            elif option == 3:
                exit("Goodbye")
            else:
                raise TypeError("Invalid choice, please choose 1, 2, or 3")
        except Exception:
            print("Invalid response, try again.  Press control + c to kill program.")
     

def readMessage(locations: dict, arr: list) -> str:
    ''' Decrypt the message embedded in the image.  Locations is the exif data stored in the image and
    arr is the image pixel data.
    '''
    return "".join([chr(arr[i, j, arr[0, 0, 0] % 3]-locations[(i,j)]) for i, j in locations])


def randomPixelSet(msg: str, arr: list, channel: int = 0) -> dict:
    ''' This function first generates the locci list which is a list of len(msg) pixel locations
    in arr (the input image).  Next a dictionary is returned where each key is an element of 
    locii and each value is the rgb value specified by the channel parameter of the pixel at the
    key location subtracted by the ascii character code of the ith element of the msg string.
    ***Note m*n <= N, where m, n = shape***
    '''
    msg = str(msg, 'utf-8')
    n, m, _ = arr.shape
    locii = sample([i for i in product(list(range(n)), list(range(m)))], len(msg))
    return {locii[i]: arr[locii[i][0], locii[i][1], channel] - ord(msg[i])
            for i in range(len(locii))}


def addRandomChannelMod(arr: list):
    ''' add a random integer 0-3 to the first pixel's (red) channel.  The resultant pixel value
    mod 3 will be the color channel we use to encrypt/ decrypt our secret message.
    '''
    k = randint(0, 3)
    arr[0, 0, 0] += k if arr[0, 0, 0] + k <= 255 else arr[0, 0, 0] - k # prevent an overflow
    return arr[0, 0, 0] % 3


def package_exif_data(locations: dict):
    ''' return pixel locations in exif format, ready to be embedded into image
    '''
    data = {
        'locations': locations, # pixels locations used for encrypt/decrypt
        'public-key': randint(0,int(1e9)), # Does nothing, used to mislead people trying to crack code.
        'private-key': randint(0,int(1e9)), # Does nothing, used to mislead people trying to crack code.
        'seed': np.random.random() # Does nothing, used to mislead people trying to crack code.
    }
    data = pickle.dumps(data)
    exif_ifd = {piexif.ExifIFD.MakerNote: data}
    return piexif.dump({"0th": {}, "Exif": exif_ifd, "1st": {},
                        "thumbnail": None, "GPS": {}})


def main():

    print("args:",argv)

    if args.write :
        img = Image.open(args.input)
        I = np.array(img)
        channel = addRandomChannelMod(I)

        msg = getUserInput()
        emsg, _ = encryption(msg)

        print("message:", msg)
        print("encrypted message:", emsg)

        locations = randomPixelSet(emsg, I, channel=channel)
        
        img = Image.fromarray(I)
        img.save(args.output,  exif=package_exif_data(locations))

        print(args.output, "saved")

    else:
        img = Image.open(args.input)
        raw = img.getexif()[piexif.ExifIFD.MakerNote]
        tags = pickle.loads(raw)

        msg = readMessage(tags["locations"], np.array(img))
        print("Message decrypted:")

        # Check for the existence of a key.pickle file 
        if os.path.isfile("key.pickle"):
            with open("key.pickle","rb") as p:
                fernet = pickle.load(p)
        else:
            raise Exception("key file error: no key.pickle file found in current directory.")

        dmsg = fernet.decrypt(msg.encode()).decode()
        print("cipher text:", msg)
        print("decrypted text:", dmsg)


main()

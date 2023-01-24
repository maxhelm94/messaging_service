import os
import urllib.request
from PIL import Image, UnidentifiedImageError
from src.data_store import data_store
from src.error import InputError
from src.other import user_exists, get_members_details, calc_involvement_rate, get_user_dict, calc_utilizaton_rate
from src import config

def users_all_v1(auth_user_id):
    """
    Returns a list of all users and their associated details.

    Arguments:
        <auth_user_id> (int)   - The u_id of the user attempting to receive all users details

    Exceptions:
        AccessError - Occurs when auth_user_id (token) is an invalid u_id (token) and does not exist

    Return Value:
        Returns a list of dictionaries where each dictionary contains users
    """

    store = data_store.get()
    user_list = store["users"]

    # # Raise AccessError if invalid auth_user_id
    # if not user_exists(user_list, auth_user_id):
    #     raise AccessError("Invalid user id")

    # Make a list of all u_ids
    all_u_ids = []
    for user in user_list:
        all_u_ids.append(user['auth_user_id'])
    
    return {'users': get_members_details(all_u_ids)}

def user_profile_v1(auth_user_id, u_id):
    """
    For a valid user, returns information about their user_id, email, first name, last name, and handle

    Arguments:
        <auth_user_id> (int)   - The u_id of the user attempting to receive a users details
        <u_id>         (int)   - The u_id of the user whom their profile will be retrieved

    Exceptions:
        InputError - Occurs when u_id does not refer to a valid user
        AccessError - Occurs when auth_user_id is an invalid u_id and does not exist

    Return Value:
        Returns a dictionary containing the u_id, email, name_first, name_last, handle_str of a user
    """
    store = data_store.get()
    user_list = store["users"]
    # # Raise AccessError if invalid auth_user_id
    # if not user_exists(user_list, auth_user_id):
    #     raise AccessError("Invalid auth user id")

    # Raise InputError if invalid u_id
    if not user_exists(user_list, u_id):
        raise InputError("Invalid user id")

    # Put u_id into a list so it can be passed into get_member_details functions which takes in a list of u_ids
    list_with_one_id = [u_id]
    # Access first dictionary since there is only 1
    return {'user': get_members_details(list_with_one_id)[0]}

def save_location(auth_user_id):
    """
    Helper function for user_profile_uploadphoto_v1().

    1. Finds and points to the photos directory, which is in the root directory
       of the project; even from the src and tests subdirectory.
    
    2. Then saves the photo as a .jpg with the user ID as its name; in a string
       pointing to the photos directory in project root.

    3. Then checks if the photos directory exists in project root. If not,
       create it.

    Returns, as a string, the entire file path of the photo.
       E.g. User's photo with ID = 1 is saved in:
            project-backend/photos/1.jpg
    """

    # Step 1:
    # Path: CWD + user ID + .jpg
    location_to_save = os.path.join(os.getcwd(), str(auth_user_id) + '.jpg')
    
    # [..., 'project-backend', (EITHER None OR 'src' OR 'tests'), '1.jpg']
    location_list = location_to_save.split('/')
    
    # Step 2:
    # If program currently in root directory
    if 'src' not in location_list and 'tests' not in location_list:
        # [..., 'project-backend', INSERT 'photos' HERE, '1.jpg']
        location_list.insert(-1, 'photos')
    
    # Else program is in either the src or tests directory
    else:
        # [..., 'project-backend', REPLACE WITH 'photos' HERE, '1.jpg']
        location_list[-2] = 'photos'

    location_to_save = '/'.join(location_list)
    
    # Step 3:
    # Remove the ID.jpg portion, to get the location of the photos directory
    location_list.pop(-1)
    location_to_save_concatenate = '/'.join(location_list)

    if os.path.exists(location_to_save_concatenate) == False:
        os.makedirs(location_to_save_concatenate)

    return location_to_save

def set_user_profile_img_url(auth_user_id, origin):
    """
    Generates a SERVER route (str) to the location of a user's profile image.

    Arguments:
        <auth_user_id> (int) - An authorised user's auth_user_id.
        <origin>       (str) - The originality of the image to use in the
                               server. If "custom" tag is active, return the
                               image matching the user's auth_user_id.
    
    Return Value:
        Returns a string with the SERVER route location of the image.
        e.g. Default = http://localhost:8068/default.jpg
        e.g. Custom  = http://localhost:8068/photos/1.jpg
    """
    
    # Custom - in /photos directory
    if origin == "custom":
        return config.url + "photos/" + str(auth_user_id) + ".jpg"
    
    # Default - in /root directory
    return config.url + "default.jpg"

def user_profile_uploadphoto_v1(auth_user_id, img_url, x_start, y_start, x_end, y_end):
    """
    Given a URL of an image on the internet, crops the image within bounds
    (x_start, y_start) and (x_end, y_end). Position (0,0) is the top left.
    Please note: the URL needs to be a non-https URL (it should just have
    "http://" in the URL. We will only test with non-https URLs.

    Arguments:
        <auth_user_id> (int) - An authorised user's auth_user_id.
        <img_url>      (str) - An image URL (should be http:// and .jpg).
        <x_start>      (int) - Starting x-coordinate for crop.
        <y_start>      (int) - Starting y-coordinate for crop.
        <x_end>        (int) - Ending x-coordinate for crop.
        <y_end>        (int) - Ending y-coordinate for crop.

    Exceptions:
        InputError - img_url returns an HTTP status other than 200. For an
                     invalid URL, will wait 5 seconds before timeout.
                   - Any of x_start, y_start, x_end, y_end are not within the
                     dimensions of the image at the URL.
                   - x_end is less than x_start or y_end is less than y_start.
                   - Image uploaded is not a .jpg.

    Return Value:
        Returns an empty dictionary.
    """

    img_url = img_url.lower()

    # Check image type (accepted extensions are .jpg and .jpeg)
    if not img_url.endswith('.jpg') and not img_url.endswith('.jpeg'):
        raise InputError("Image uploaded is not a JPG.")

    # Check of image URL is valid
    # https://docs.python.org/3/library/urllib.request.html#urllib.response.addinfourl.status
    http_wrong_status = "img_url returned an HTTP status other than 200."
    
    try:
        with urllib.request.urlopen(img_url, timeout = 5) as img:
            img_status_code = img.getcode()
            img_status_code = img_status_code  # Pylint ARGH
            # if img_status_code != 200:
            #     raise InputError(http_wrong_status)
    except (urllib.error.HTTPError) as e:
        raise InputError(http_wrong_status) from e

    image_location = save_location(auth_user_id)

    # Saves the downloaded image into project-backend/photos
    urllib.request.urlretrieve(img_url, image_location)
    
    try:
        image = Image.open(image_location)
    except (UnidentifiedImageError) as e:
        raise InputError(http_wrong_status) from e

    # First check image dimensions vs. input parameters
    width, height = image.size  # Both type == int
    
    if int(x_end) < int(x_start):
        raise InputError("x_end less than x_start.")
    if int(y_end) < int(y_start):
        raise InputError("y_end less than y_start.")

    if int(x_start) not in range(0, width + 1):
        raise InputError("x_start not within the dimensions of the image.")
    if int(x_end) not in range(0, width + 1):
        raise InputError("x_end not within the dimensions of the image.")
    if int(y_start) not in range(0, height + 1):
        raise InputError("y_start not within the dimensions of the image.")
    if int(y_end) not in range(0, height + 1):
        raise InputError("y_end not within the dimensions of the image.")

    # Start cropping procedure
    try:
        cropped = image.crop((int(x_start), int(y_start), int(x_end), int(y_end)))
        cropped.save(image_location)
    except (SystemError) as e:
        raise InputError("Crop dimensions are not relatively valid.") from e

    # Assign this cropped image to the user's details in the data_store
    store = data_store.get()
    
    for user in store["users"]:
        if user["auth_user_id"] == auth_user_id:
            user["profile_img_url"] = set_user_profile_img_url(auth_user_id, "custom")
            break
    
    data_store.set(store)

    return {}

def user_stats_v1(auth_user_id):
    """
    Fetches the required statistics about the user with auth user id's use of UNSW Streams

    Arguments:
        <auth_user_id> (int)   - The u_id of the user attempting to receive their stats

    Exceptions:
        None

    Return Value:
        Returns a dictionary containing the keys 'channels_joined', 'dms_joined', 'messages_sent' and 'involvement_rate' inside a wrapper dict

    """
    user = get_user_dict(auth_user_id)

    user['stats']['involvement_rate'] = calc_involvement_rate(auth_user_id)

    return {'user_stats': user['stats']}

def users_stats_v1(auth_user_id):
    """
    Fetches the required statistics about the use of UNSW Streams.

    Arguments:
        <auth_user_id> (int)   - The u_id of the user attempting to receive the workspace's stats

    Exceptions:
        None

    Return Value:
        Returns a dictionary containing the keys 'channels_exist', 'dms_exist', 'messages_exist' and 'utilization_rate' inside a wrapper dict

    """
    store = data_store.get()
    workspace_stats = store['workspace_stats']
    workspace_stats['utilization_rate'] = calc_utilizaton_rate()

    return {'workspace_stats': workspace_stats}

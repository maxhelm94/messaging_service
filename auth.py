from src.data_store import data_store
from src.error import InputError
from src.other import what_time_is_it
from src.user import set_user_profile_img_url
import re
import hashlib
import jwt
import smtplib, ssl
import random, string, time


SUPERSECRETPASSWORD = "StampsWithAlpacas"



def email_is_invalid(email, auth_user_id):
    # check if mail address was already used for registration
    # and output error if it is
    for user in data_store.get()['users']:
        if user['email'] == email and auth_user_id != user['auth_user_id']:
            return True
    
    # check if email has the right format
    mail_regex = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    if (re.fullmatch(mail_regex, email)):
        pass
    else:
        # email does not have the right format
        return True
    return False

def password_length_invalid(password):
    if len(password) < 6:
        return True
    return False

def name_has_incorrect_length(name_first, name_last):
    # check if first name has the right size
    if not(len(name_first) > 0 and len(name_first) < 51):
        return True

    # check if last name has the right size
    if not(len(name_last) > 0 and len(name_last) < 51):
        return True
    return False


def generate_name_handle(name_first, name_last):
    # create name_handle cut it if it's longer than 20 chars
    name_handle = name_first + name_last
    
    # remove all special characters from the name_handle
    name_handle = re.sub(r'\W+', '', name_handle)
    name_handle = re.sub(r'_+', '', name_handle)
    # change all letters to lower case
    name_handle = name_handle.lower()
    
    # cut the name_handle if it's longer than 20 chars
    if len(name_handle) > 20:
        name_handle = name_handle[:20]
    
    # if another user uses the same name_handle, then the first user will
    # have no index; user 2 will have index 0 and user 3 will have index 1
    i = -1 
    while 1:
        taken = False
        for user in data_store.get()['users']:
            # look if name_handle was used previously used
            if user['name_handle'] == name_handle:
                # set taken to True if the name_handle is already taken
                taken = True
        if taken:
            # remove the index from the name_handle
            if i >= 0:
                for _ in range(len(str(i))):
                    name_handle = name_handle[0:-1]
            # add the new index to the name_handle
            i += 1
            name_handle = name_handle + str(i)
        else:
            return name_handle

def generate_session_id():
    # generates a session_id
    # the session_id will be the highest session_id that is currently active + 1
    data_save = data_store.get()
    session_id = int(data_save['session_id']) + 1
    data_save['session_id'] = session_id 
    data_store.set(data_save)

    return session_id



def auth_login_v1(email, password):
    """
    Let a registered user login, if he enters his/her email and password 
    correctly.

    Arguments:
        <email> (str) - The email is a string with a very particular design.
         Regarding the string design, see description of auth_register_v1. 
        <password> (str) - the password can be any string containing ASCII 
         characters. The string must be at least 6 chars long.

    Exceptions:
        InputError - The input error occurs if
         either the password does not fit the account with that email address,
         or the email entered is not valid.

    Return Value:
        Returns a dictionary with 'auth_user_id' as only key that has the
        value of the user_id of the user that logged in. 
    """


    # search the data_store users list for this user
    # variable x saves the outcome of the function; it stays 0 if the email
    # address cannot be found, becomes 1 if the password does not match to 
    # the account or becomes 2 if the login is successful
    x = 0
    for user in data_store.get()['users']:
        # if only email can be found, then the password does not match to
        # this user
        if user['email'] == email:
            x = 1
        # if both match to one user, login is successful
        if user['email'] == email and user['password'] == hashlib.sha256(password.encode()).hexdigest():
            x = 2
            # save this particular user_id of that user
            user_id = user['auth_user_id']
    
    if x == 0:
        raise InputError('Account does not exist or email is wrong')
    if x == 1:
        raise InputError('Password is wrong')

    data_save = data_store.get()
    # create a new session_id
    session_id = generate_session_id()
    # save that new session_id in the session_id list of the user
    for user in data_save['users']:
        if email == user['email']:
            user['session_ids'].append(session_id)
    data_store.set(data_save)

    token = jwt.encode({'auth_user_id': str(user_id), 'session_id': str(session_id)}, SUPERSECRETPASSWORD, algorithm="HS256") 


    return {'token': token, 'auth_user_id': user_id}



def auth_register_v1(email, password, name_first, name_last):
    """
    Registers a new user if all input fits the format. The user will be saved
    as part of the users list in the data_store dictionaray.

    Arguments:
        <email> (str) - The email is a string with a very particular design.
         There has to be at least one char before an '@' char, at least one 
         char after it, then a '.', and two letters in the end. 
        <password> (str) - the password can be any string containing ASCII 
         characters. The string must be at least 6 chars long.
        <name_first> (str) - The first name is a string of ASCII characters,
         that has a length of 1-50 chars.
        <name_last> (str) - The last name is a string of ASCII characters,
         that has a length of 1-50 chars.

    Exceptions:
        InputError - The input error occurs if
         - the email does not fit the previously described format
         - the email that is used, already exists
         - the first or last name does not meet the required length
         - the password is too short (has less than 6 chars)

    Return Value:
        Returns a dictionary with <auth_user_id> as only key that has the
        value of a generated user_id. This user_id will be of type int.
    """

    # check if password is long enough
    if password_length_invalid(password):
        raise InputError('Password has to be at least 6 characters long')
    
    # check if first name has the right size
    if name_has_incorrect_length(name_first, name_last):
        raise InputError('Each name has to be between 1 and 50 chars long')

    # encrypt the password
    password = hashlib.sha256(password.encode()).hexdigest()

    # create name_handle
    name_handle = generate_name_handle(name_first, name_last)

    # check if there are other registered users; if not, go to else statement
    if data_store.get()['users']:
        user_id = len(data_store.get()['users']) + 1
        # if there exists another user already, then the permission_id will 
        # be automatically set to 2
        permission_id = 2
    
    else:
        # else statement runs if no user was registered previously
        # then the first user gets user_id 1 and permission_id 1
        user_id = 1
        permission_id = 1

    # check if email is valid
    if email_is_invalid(email, -1):
        raise InputError('email is not valid or taken')

    session_id = generate_session_id()
    token = jwt.encode({'auth_user_id': str(user_id), 'session_id': str(session_id)}, SUPERSECRETPASSWORD, algorithm="HS256")

    utc_timestamp = what_time_is_it()

    # create a new dictionary for the new user with all his/her details
    new_user = {
            'name_first': name_first,
            'name_last': name_last,
            'name_handle': str(name_handle),
            'email': email,
            'password': str(password),
            'auth_user_id': user_id,
            'permission_id': permission_id,
            'session_ids': [session_id],
            'reset_password': "",
            'notifications': [],
            'stats': {
                'channels_joined': [
                    {
                        'num_channels_joined': 0,
                        'time_stamp': utc_timestamp
                    }
                ],
                'dms_joined': [
                    {
                        'num_dms_joined': 0,
                        'time_stamp': utc_timestamp
                    }
                ],
                'messages_sent': [
                    {
                        'num_messages_sent': 0,
                        'time_stamp': utc_timestamp
                    }
                ]
            },
            'profile_img_url': set_user_profile_img_url(user_id, 'default')
        }
    
    # add the new dictionary with the user's details to the data_store list
    data_save = data_store.get()
    data_save['users'].append(new_user)
    data_store.set(data_save)

    # add appropriate workplace_stats fields now that a 1st user is registered
    if new_user['auth_user_id'] == 1:
        workspace_stats = {"channels_exist": [{'num_channels_exist': 0,
                                               'time_stamp': utc_timestamp}],
                           "dms_exist": [{'num_dms_exist': 0,
                                          'time_stamp': utc_timestamp}],
                           "messages_exist": [{'num_messages_exist': 0,
                                               'time_stamp': utc_timestamp}]}
        
        store = data_store.get()
        store['workspace_stats'] = workspace_stats
        data_store.set(store)

    return {'token': token, 'auth_user_id': user_id}


def auth_passwordreset_request(email):
    """
    Given an email address, if the user is a registered user, sends them an
    email containing a specific secret code, that when entered in auth/passwordreset/reset,
    shows that the user trying to reset the password is the one who got sent this email.

    Arguments:
        <email> (str) - is a string with a specific format described in auth_register_v1.
         The user passes in the email, so we can send him/her a reset code. The email has
         to belong to a registered account.

    Exceptions:
        There are no errors raised because of security concerns; however, the function will
        terminate if the email does not belong to any registered user, or the user has an
        active session.

    Return Value:
        The function does not return anything.
    """
    
    # generate a random alphanumeric 10 char password
    reset_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    #reset_password = "abcdefghij"
    x = 1

    # assess whether email exists and if user has no active sessions; otherwise quit
    data_save = data_store.get()
    for user in data_save['users']:
        if user['email'] == email:
            if user['session_ids'] == []:
                x = 0
                user['reset_password'] = reset_password
    if x:
        return
    
    data_store.set(data_save)

    port = 465  # For SSL
    password = "trampstamphussies"
    # Create a secure SSL context
    context = ssl.create_default_context()

    sender_email = "alpacastampclub@gmail.com"
    receiver_email = email
    message = f"Your temporary password is {reset_password}"

    # connect to gmail server
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login("alpacastampclub@gmail.com", password)
        server.sendmail(sender_email, receiver_email, message)
    
    return



def auth_passwordreset_reset(reset_code, new_password):
    """
    Given a reset code for a user, set that user's new password to the
    password provided.

    Arguments:
        <reset_code> (str) - the string that is sent to the user by email,
         when he/she called auth_password_request; it is a 10 char alphanumeric
         string 
        <new_password> (str) - is a string that the user provides. It has to
         be longer than 6 chars and will be the new password of the user

    Exceptions:
        InputError - The input error occurs if
         - reset_code is not a valid reset code
         - password entered is less than 6 characters long

    Return Value:
        The function does not return anything.
    """

    # check if the password has the appropriate length by using the helper function 
    if password_length_invalid(new_password):
        raise InputError('Password has to be at least 6 characters long')
    
    # assess if the reset code is valid; if it is, set the new password as the
    # user's password and delete the reset code; if not raise an input error
    x = 1
    data_save = data_store.get()
    for user in data_save['users']:
        if user['reset_password'] == reset_code:
            x = 0
            user['reset_password'] = ""
            user['password'] = str(hashlib.sha256(new_password.encode()).hexdigest())
    if x:
        raise InputError("reset_code is wrong")
    data_store.set(data_save)
    return

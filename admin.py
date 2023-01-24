from src.data_store import data_store
from src.error import AccessError, InputError
from src.other import user_exists
from src.channel import is_global_owner

# Permission IDs:
GLOBAL_OWNER = 1
GLOBAL_MEMBER = 2

def is_sole_global_owner(users, u_id):
    """
    A function to determine if u_id is the sole global owner.
    I'm sure this can be cleaned up, but it should work for now.
    
    Arguments: 
        - users (list of dicts)
        - u_id (int)
    Return: Boolean
    """
    is_sole_global_owner = True
    for user in users:
        if user['auth_user_id'] == u_id and user['permission_id'] != GLOBAL_OWNER:
            # u_id is not a global owner
            is_sole_global_owner = False
        elif user['auth_user_id'] != u_id and user['permission_id'] == GLOBAL_OWNER:
            # Another user is a global owner
            is_sole_global_owner = False
    
    return is_sole_global_owner

def admin_userpermission_change_v1(auth_user_id, u_id, permission_id):
    """
    Allows an admin change the permission id of a user.

    Arguments:
        auth_user_id  (str)  - the user id of the member joining the channel
        u_id          (int)  - the user id of the user having their permission changed
        permission_id (int)  - the permission id
        
    Exceptions:
        InputError  - Occurs when:
            a) u_id does not refer to a valid user
            b) u_id refers to a user who is the only global owner and they are being demoted to a user
            c) permission_id is invalid
        AccessError - Occurs when:
            a) the authorised user is not a global owner

    Return Value:
        Returns {} always. (an empty dictionary)
    """

    store = data_store.get()
    users = store['users']
    
    # AccessError if auth_user_id doesn't exist: 
    # NOTE: Shouldn't ever reach here as this is checked in is_valid_token() in other.py
    # if not user_exists(users, auth_user_id):
    #     raise AccessError("Auth user does not exist.")
        
    # AccessError if the authorised user is not a global owner
    if not is_global_owner(users, auth_user_id):
        raise AccessError("User doesn't have permission to change another user's permissions")
    
    # InputError if u_id does not refer to a valid user
    if not user_exists(users, u_id):
        raise InputError("Trying to change permissions of a user that does not exist.")
    
    # InputError if u_id refers to a user who is the only global owner and they are being demoted to a user
    if permission_id == GLOBAL_MEMBER and is_sole_global_owner(users, u_id):
        raise InputError("Cannot demote the sole global owner.")
    
    # InputError if permission_id is invalid
    if permission_id not in [GLOBAL_MEMBER, GLOBAL_OWNER]:
        raise InputError("Permission_id is invalid.")
    
    # Change the permission of u_id to permission_id:
    for user in users:
        if user['auth_user_id'] == u_id:
            user['permission_id'] = permission_id
    
    # Store the updated data:
    store['users'] = users
    data_store.set(store)
    
    return {}
    
def admin_user_remove_v1(auth_user_id, u_id):
    """
    Given a user by their u_id, remove them from the Streams. This means they
    should be removed from all channels/DMs, and will not be included in the
    list of users returned by users/all. Streams owners can remove other Streams
    owners (including the original first owner). Once users are removed, the
    contents of the messages they sent will be replaced by 'Removed user'. Their
    profile must still be retrievable with user/profile, however name_first
    should be 'Removed' and name_last should be 'user'. The user's email and
    handle should be reusable.

    Arguments:
        auth_user_id (str)  - the user id of the member joining the channel
        u_id         (int)  - the user who is to be removed from UNSW Streams.
        
    Exceptions:
        InputError  - Occurs when:
            a) u_id does not refer to a valid user.
            b) u_id refers to a user who is the only global owner.
        AccessError - Occurs when:
            a) The authorised user is not a global owner.

    Return Value:
        Returns {} always. (an empty dictionary)
    """
        
    # Get and extract data from the data_store
    store = data_store.get()
    store_users = store['users']
    store_channels = store['channels']
    store_dms = store['dms']

    # Raise InputError if invalid auth_user_id
    # if not user_exists(store_users, auth_user_id):
    #     raise InputError('Invalid auth_user_id')
    
    # Raise InputError if invalid u_id
    if not user_exists(store_users, u_id):
        raise InputError('Invalid user_id')

    # Raise AccessError if auth_user_id is not a global owner
    if not is_global_owner(store_users, auth_user_id):
        raise AccessError("auth_user_id is not a global owner")

    # Counting the number of global owners in the data_store, to potentially
    # raise an InputError if there is only one.
    permission_id_count = 0
    for indv_user in store_users:
        if indv_user['permission_id'] == 1:
            permission_id_count += 1
    for indv_user in store_users:
        if permission_id_count == 1 and u_id == 1:
            raise InputError("u_id is the only global owner left")

    # Removed user data_store[users] template
    removed_user = {
        'name_first': "Removed",
        'name_last': "user",
        'name_handle': "",
        'email': "",
        'password': "",
        'auth_user_id': u_id,  # Maintain existing ID
        'permission_id': 2,    # From GLOBAL_OWNER 1 to GLOBAL_MEMBER 2
        'session_ids': [],
        'notifications': [],
        'stats': {},
        'profile_img_url': ""
    }

    # Search though data_store[users] to remove u_id person
    for i, indv_user in enumerate(store_users):
        if indv_user['auth_user_id'] == u_id:
            # Replace existing record with the removed_user template
            store['users'][i] = removed_user
            # break

    # Search through data_store[channels] to remove u_id person, and replace
    # their messages
    for i, indv_channel in enumerate(store_channels):
        # Loop through owner_members list to remove u_id member
        for j, owner in enumerate(indv_channel['owner_members']):
            if owner == u_id:
                store['channels'][i]['owner_members'].pop(j)
                break

        # Loop through all_members list to remove u_id member
        for j, member in enumerate(indv_channel['all_members']):
            if member == u_id:
                store['channels'][i]['all_members'].pop(j)
                break

        # Loop through all channel messages and replace u_id's messages
        for j, message in enumerate(indv_channel['messages']):
            if message['u_id'] == u_id:
                # Replace u_id's message u_id with -1, and message with
                # "Removed user"
                store['channels'][i]['messages'][j]['u_id'] = -1
                store['channels'][i]['messages'][j]['message'] = "Removed user"
        
    # Search through data_store[dms] to remove u_id person, and replace their
    # DMs
    for i, indv_dm in enumerate(store_dms):
        # Set DMs with owner_id matching u_id to -1
        if indv_dm['owner_id'] == u_id:
            store['dms'][i]['owner_id'] = -1

        # Loop through u_ids list to remove u_id user
        for i, user in enumerate(indv_dm['u_ids']):
            if user == u_id:
                store['dms'][i]['u_ids'].pop(i)

        # Loop through all DMs and replace u_id's DMs
        for i, dm in enumerate(indv_dm['messages']):
            if dm['u_id'] == u_id:
                # Replace u_id's DM u_id with -1, and DM with "Removed user"
                store['dms'][i]['messages'][i]['u_id'] = -1
                store['dms'][i]['messages'][i]['message'] = "Removed user"
    
    data_store.set(store)

    return {}

from abc import ABCMeta, abstractmethod, abstractproperty

def intersection(collection, pool):
    pool = set(pool)
    if isinstance(collection, frozenset):
        return frozenset(collection & pool)
    if isinstance(collection, set):
        return collection & pool
    elif isinstance(collection, dict):
        return {x: collection[x] for x in collection if x in pool}
    elif isinstance(collection, tuple):
        return tuple(x for x in collection if x in pool)
    else:
        return [x for x in collection if x in pool]

class RoomObserver(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def watch(self, event_callback):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def ping_string(self, user_id, quote=False):
        pass

    def ping_strings(self, user_ids, quote=False):
        return [self.get_ping_string(u, quote) for u in user_ids]

    def classify_user_ids(self, user_ids):
        '''Classify each of the given user_ids as present (currently in the room),
        pingable (but not currently in the room), or unreachable (not pingable
        and not currently in the room). "Pingable" does not count superpings,
        which can reach anyone.'''
        present = self.present_user_ids
        pingable = self.pingable_user_ids
        absent = set(user_ids) - present - pingable
        return (
            intersection(user_ids, present),
            intersection(user_ids, pingable),
            intersection(user_ids, absent)
            )

    @abstractproperty
    def present_user_ids(self):
        '''Return a `set` of the user IDs present in the chat room.'''
        pass

    @abstractproperty
    def pingable_user_ids(self):
        '''Return a `set` of the user IDs pingable in the chat room (not counting
        superpings). This _should_ be a superset of ``present_user_ids``.'''
        pass

    @abstractproperty
    def observer_active(self):
        return True

class RoomParticipant(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def send(self, message, reply_target=None):
        pass

    def close(self):
        # The default implementation here is intentionally the same as that in
        # RoomObserver, so that a single class can inherit from both, not
        # override close(), and have no conflicts.
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    @abstractproperty
    def participant_active(self):
        return True

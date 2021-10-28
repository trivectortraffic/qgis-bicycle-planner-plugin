MAX_DISTANCE_M = 30000

poi_category_classes = {
    'leisure': [
        'attraction',
        'cinema',
        'community_centre',
        'dog_park',
        'garden_centre',
        'golf_course',
        'museum',
        'park',
        'picnic_site',
        'pitch',
        'playground',
        'sports_centre',
        'theatre',
        'track',
    ],
    'shopping': [
        'bicycle_shop',
        'clothes',
        'gift_shop',
        'mobile_phone_shop',
        'outdoor_shop',
        'supermarket',
        'toy_shop',
        'video_shop',
    ],
    'services': [
        'atm',
        'bank',
        'bakery',
        'cafe',
        'car_dealership',
        'car_wash',
        'car_rental',
        'dentist',
        'fast_food',
        'hairdresser',
        'kindergarten',
        'kiosk',
        'laundry',
        'library',
        'pharmacy',
        'police',
        'post_box',
        'post_office',
        'pub',
        'recycling',
        'recycling_paper',
        'restaurant',
        'school',
        'toilet',
        'town_hall',
        'veterinary',
    ],
    'touring': [
        'artwork',
        'chalet',
        'castle',
        'camp_site',
        'fountain',
        'hostel',
        'hotel',
        'ruins',
        'tourist_info',
        'tower',
        'viewpoint',
    ],
}

poi_categories = set(poi_category_classes.keys()) | {'work', 'school'}

poi_class_map = {v: c for c, vs in poi_category_classes.items() for v in vs}

# TODO: integrate into common structure to prevent key mismatch (add tests)
# Beta_p
poi_gravity_values = {
    'work': -0.0370,
    'school': -0.0370,
    'leisure': -0.0351,
    'shopping': -0.0833,
    'services': -0.0833,
    'touring': -0.0351,
}

# T_p
trip_generation = {
    'work': 1.52,
    'school': 1.52,
    'shopping': 0.18,
    'services': 0.18,
    'touring': 0.07,
    'leisure': 0.4,
}

# alpha_m
mode_split = {
    'bike': 0.8,
    'ebike': 0.2,
}

mode_params_bike = {
    'work': [
        0.5949,
        -7.2431,
        0.0574,
        -0.1844,
    ],
    'services': [
        0.0454,
        -3.7518,
        -1.6994,
        -2.4196,
    ],
    'shopping': [
        -0.4439,
        -8.2956,
        -2.0871,
        1.5641,
    ],
    'school': [0.9115, -7.6363, -1.2157, -0.3794],
    'leisure': [
        0.5687,
        -0.9215,
        0.01977,
        -3.3317,
    ],
    'touring': [
        -0.9041,
        0.3791,
        -1.9409,
        5.5269,
    ],
}
mode_params_ebike = {
    'work': [
        0.0717,
        -2.3744,
        -1.6408,
        -1.7157,
    ],
    'services': [
        -0.2979,
        -2.1398,
        -1.3330,
        -1.5403,
    ],
    'shopping': [
        -0.6498,
        -3.1822,
        -0.9767,
        0.0433,
    ],
    'school': [-0.7878, -2.7428, -1.2542, -0.3794],
    'leisure': [
        -0.7290,
        -1.4593,
        -0.0195,
        -0.5882,
    ],
    'touring': [
        -3.3602,
        2.2010,
        -2.5280,
        4.3107,
    ],
}

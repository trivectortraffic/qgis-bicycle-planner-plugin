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

poi_categories = set(poi_category_classes.keys())

poi_class_map = {v: c for c, vs in poi_category_classes.items() for v in vs}

# TODO: integrate into common structure to prevent key mismatch (add tests)
poi_gravity_values = {
    'leisure': -0.0351,
    'shopping': -0.0833,
    'services': -0.0833,
    'touring': -0.0351,
}

mode_params_bike = {
    'shopping': [
        -0.44391129463248735,
        0.045421282463330465,
        -3.904112256228761,
        0.5687733506577125,
    ],
    'services': [
        -8.295618349118543,
        -3.751848767649791,
        0.3791578463667172,
        -0.9215795742380404,
    ],
    'touring': [
        -2.0871942229142797,
        -1.6994613073684237,
        -1.940943420795848,
        0.019770984624589937,
    ],
    'leisure': [
        1.5641575146847442,
        -2.4196921105723215,
        5.526990391189266,
        -3.331767479111909,
    ],
}
mode_params_ebike = {
    'shopping': [
        -0.6498748953606043,
        -0.29797345841414963,
        -3.3602305317530834,
        -0.7290932553055972,
    ],
    'services': [
        -3.1822681067845404,
        -2.1398819794608994,
        2.201028708826716,
        -1.4593795193621433,
    ],
    'touring': [
        -0.976798293893275,
        -1.3330152115670482,
        -2.5280686380753137,
        -0.019578406245738936,
    ],
    'leisure': [
        0.04333028543699834,
        -1.5403262612251727,
        4.310711954186476,
        -0.588298193854497,
    ],
}

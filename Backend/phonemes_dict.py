"""
Manually curated phoneme dictionary.

Each phoneme contains:
- patterns: common spelling patterns with example words
- spelling: IPA transcriptions mapped to (correct_spelling, wrong_option1, wrong_option2)
- homophones: phonemic transcriptions mapped to sets of homophone spellings
- api: query term for Free Dictionary API (UK audio)
"""

phonemes = {
    'ɔ:': {
        'patterns': {
            'aw': ('law', 'yawn', 'draw'),
            'ore': ('core', 'snore', 'before'),
            'oar': ('boar', 'coarse', 'hoard'),
            'or': ('port', 'absorb', 'corn'),
            'au': ('august', 'autumn', 'flaunt'),
            'oor': ('door', 'boor', 'moor'),
            'our': ('mourn', 'course', 'four'),
            'war': ('war', 'award', 'swarm'),
        },
        'spelling': {
            "/'ɔ:də/": ('order', 'aurder', 'awder'),
            "/'kɔ:ʃən/": ('caution', 'courtion', 'coretion'),
            '/wɔ:d/': ('ward', 'waud', 'woard'),
            '/lɔ:ntʃ/': ('launch', 'lornch', 'lawnch'),
            '/dɔ:n/': ('dawn', 'dorn', 'daun'),
            '/dʒɔ:/': ('jaw', 'jore', 'joor'),
            "/dɪ'vɔ:s/": ('divorce', 'divauce', 'divawce'),
            "/ə'fɔ:d/": ('afford', 'affawd', 'affaud'),
            '/stɔ:/': ('store', 'stoar', 'stour'),
            '/swɔ:/': ('swore', 'swar', 'swor'),
            '/kɔ:n/': ('corn', 'cawn', 'coarn'),
            "/ə'plɔ:d/": ('applaud', 'applord', 'applawed'),
        },
        'homophones': {
            '/ɔ:/': {'or', 'oar', 'awe', 'ore'},
            '/sɔ:/': {'saw', 'sore', 'soar'},
            '/bɔ:d/': {'bored', 'board'},
            '/flɔ:/': {'floor', 'flaw'},
            '/ʃɔ:/': {'shore', 'sure'},
            '/pɔ:/': {'poor', 'paw', 'pore', 'pour'},
            '/sɔ:s/': {'sauce', 'source'},
            "/'mɔ:nɪŋ/": {'morning', 'mourning'},
            '/stɔ:k/': {'stalk', 'stork'},
            '/wɔ:/': {'war', 'wore'},
        },
        'api': 'or'
    },
    'ɜ:': {
        'patterns': {
            'er + consonant': ('alert', 'deserve', 'universe'),
            'ir + consonant': ('girl', 'third', 'dirt'),
            'wor + consonant': ('world', 'work', 'worse'),
            'ur + consonant': ('curl', 'burden', 'lurk'),
            'ear + consonant': ('pearl', 'hearse', 'learn'),
        },
        'spelling': {
            '/wɜ:m/': ('worm', 'wearm', 'werm'),
            '/ʃɜ:t/': ('shirt', 'shert', 'shurt'),
            '/bɜ:st/': ('burst', 'birst', 'berst'),
            '/pɜ:k/': ('perk', 'purk', 'pirk'),
            '/fɜ:m/': ('firm', 'furm', 'ferm'),
            '/bɜ:d/': ('bird', 'burd', 'berd'),
            '/tʃɜ:tʃ/': ('church', 'chearch', 'chirch'),
            "/'mɜ:də/": ('murder', 'mirder', 'mearder'),
            '/tʃɜ:p/': ('chirp', 'churp', 'cherp'),
            '/mɜ:dʒ/': ('merge', 'murge', 'mirge'),
            "/'sɜ:tən/": ('certain', 'surtain', 'ceartain'),
            "/rɪ'zɜ:v/": ('reserve', 'researve', 'resurve'),
        },
        'homophones': {
            '/hɜ:d/': {'heard', 'herd'},
            '/fɜ:/': {'fir', 'fur'},
            '/wɜ:d/': {'word', 'whirred'},
            '/kɜ:b/': {'kerb', 'curb'},
        },
        'api': 'er'
    },
    'eə': {
        'patterns': {
            'are': ('dare', 'stare', 'ware'),
            'air': ('affair', 'chair', 'repair'),
            'ear': ('swear', 'wear', 'bear'),
        },
        'spelling': {
            '/leə/': ('lair', 'lare', 'lere'),
            '/preə/': ('prayer', 'prayrre', 'prair'),
            "/ˌvedʒə'teəriən/": ('vegetarian', 'vegetearian', 'vegetairian'),
            "/'peərənt/": ('parent', 'pairent', 'perent'),
            "/'veəri/": ('vary', 'varey', 'veary'),
            '/keə/': ('care', 'cair', 'kear'),
            "/rɪ'peə/": ('repair', 'repare', 'repere'),
            "/'feəri/": ('fairy', 'farey', 'fairry'),
            "/ə'feə/": ('affair', 'affare', 'affear'),
            '/ʃeə/': ('share', 'shair', 'shaire'),
            '/reə/': ('rare', 'rair', 'rere'),
            '/skweə/': ('square', 'squair', 'squear'),
        },
        'homophones': {
            '/feə/': {'fair', 'fare'},
            '/peə/': {'pare', 'pair', 'pear'},
            '/heə/': {'hair', 'hare'},
            '/steə/': {'stare', 'stair'},
            '/fleə/': {'flair', 'flare'},
        },
        'api': 'air'
    },
    'i:': {
        'patterns': {
            'ee': ('green', 'proceed', 'tree'),
            'ie': ('believe', 'grief', 'priest'),
            'ea': ('each', 'bleak', 'dream'),
            'e.e': ('complete', 'phoneme', 'theme'),
            'i.e': ('police', 'fatigue', 'unique'),
            'ei': ('ceiling', 'caffeine', 'deceit'),
        },
        'spelling': {
            '/tʃi:t/': ('cheat', 'cheet', 'chete'),
            "/ə'tʃi:v/": ('achieve', 'acheive', 'achive'),
            '/fli:t/': ('fleet', 'fleat', 'fliet'),
            "/kən'si:t/": ('conceit', 'conciet', 'concete'),
            '/pli:/': ('plea', 'plee', 'ply'),
            "/kən'si:v/": ('conceive', 'concieve', 'conceave'),
            "/'prəʊti:n/": ('protein', 'protene', 'proteine'),
            '/gi:s/': ('geese', 'gease', 'gese'),
            "/ɪm'pi:tʃ/": ('impeach', 'impeech', 'impeche'),
            "/ɪk'stri:m/": ('extreme', 'extream', 'extriem'),
            "/rɪ'si:v/": ('receive', 'recieve', 'reseeve'),
            '/skwi:k/': ('squeak', 'squeke', 'squeek'),
        },
        'homophones': {
            '/si:/': {'sea', 'see'},
            '/pi:/': {'pea', 'pee'},
            '/bi:t/': {'beet', 'beat'},
            '/bi:/': {'bee', 'be'},
            '/ri:d/': {'read', 'reed'},
            '/si:m/': {'seam', 'seem'},
            '/fli:/': {'flee', 'flea'},
        },
        'api': 'e'
    },
}

from sanctions_toolkit.normalize import extract_years, normalize_name


def test_armenian_and_latin_converge():
    assert normalize_name("Արամ Թեստյան") == normalize_name("Aram Testyan") == "aram testyan"


def test_cyrillic_to_latin():
    assert normalize_name("Иван Иванович Тестов") == "ivan ivanovich testov"


def test_variants_and_particles_are_folded():
    assert normalize_name("Mohammed Al-Testani") == "muhammad testani"
    assert normalize_name("Mohamed El Testani") == "muhammad testani"


def test_accents_and_punctuation():
    assert normalize_name("Zoë  O'Brien-Müller") == "zoe o brien muller"


def test_unsupported_script_returns_empty():
    assert normalize_name("محمد") == ""


def test_extract_years():
    assert extract_years("1970-05-04") == {1970}
    assert extract_years("04.05.1970") == {1970}
    assert extract_years("1972-1974") == {1972, 1973, 1974}
    assert extract_years("") == set()

from rutanorte_dq.identifiers import valid_curp, valid_email, valid_phone_mx, valid_rfc


def test_rfc_accepts_fisica_and_moral_shapes():
    assert valid_rfc("GARC850101AB1", kind="fisica")
    assert valid_rfc("NPR200315AB1", kind="moral")
    assert not valid_rfc("GARC850101AB1", kind="moral")
    assert not valid_rfc("BADRFC", kind="fisica")


def test_rfc_rejects_impossible_dates():
    assert not valid_rfc("GARC850231AB1", kind="fisica")
    assert valid_rfc("GARC850228AB1", kind="fisica")


def test_curp_shape_and_date():
    assert valid_curp("GARC850101HDFRRL09")
    assert not valid_curp("NOTACURP")
    assert not valid_curp("GARC850231HDFRRL09")


def test_contact_formats():
    assert valid_email("ana.garcia.2026101001@example.com")
    assert not valid_email("not-an-email")
    assert valid_phone_mx("+525512345678")
    assert not valid_phone_mx("12345")
    assert not valid_phone_mx("+520012345678")

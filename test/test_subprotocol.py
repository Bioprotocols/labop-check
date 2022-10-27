import labop
import sbol3
import labop_check.labop_check as pc


def _make_dummy_protocol(id, doc):
    subprotocol1 = labop.Protocol(id, name=id)
    doc.add(subprotocol1)
    action1 = labop.Primitive(f"action1_{id}")
    doc.add(action1)
    subprotocol1.primitive_step(f"action1_{id}")
    return subprotocol1


def test_subprotocol_simple():
    #############################################
    # set up the document
    print("Setting up document")
    doc = sbol3.Document()
    sbol3.set_namespace("https://bbn.com/scratch/")

    #############################################
    #############################################
    # Create the protocol
    print("Creating protocol")
    protocol = labop.Protocol("top_protocol")
    protocol.name = "simple subprotocol"

    #############################################
    # Create the subprotocol

    subprotocol1 = _make_dummy_protocol("subprotocol1", doc)
    sub_invocation1 = protocol.primitive_step(subprotocol1)

    subprotocol2 = _make_dummy_protocol("subprotocol2", doc)
    sub_invocation2 = protocol.primitive_step(subprotocol2)

    doc.add(protocol)

    ########################################
    # Validate and write the document
    print("Validating and writing protocol")
    v = doc.validate()
    assert len(v) == 0, "".join(f"\n {e}" for e in v)

    schedule, graph = pc.check_doc(doc)
    assert schedule


def test_subprotocol_nested():
    #############################################
    # set up the document
    print("Setting up document")
    doc = sbol3.Document()
    sbol3.set_namespace("https://bbn.com/scratch/")

    #############################################
    #############################################
    # Create the protocol
    print("Creating protocol")
    protocol = labop.Protocol("top_protocol")
    protocol.name = "nested subprotocol"

    #############################################
    # Create the subprotocol

    subprotocol1 = _make_dummy_protocol("subprotocol1", doc)
    sub_invocation1 = protocol.primitive_step(subprotocol1)

    subprotocol2 = _make_dummy_protocol("subprotocol2", doc)
    sub_invocation2 = subprotocol1.primitive_step(subprotocol2)

    doc.add(protocol)

    ########################################
    # Validate and write the document
    print("Validating and writing protocol")
    v = doc.validate()
    assert len(v) == 0, "".join(f"\n {e}" for e in v)

    schedule, graph = pc.check_doc(doc)
    assert schedule

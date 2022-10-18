import os
import tempfile
import unittest
import filecmp
import sbol3
import labop
import labop_time as labopt
import tyto


class TestLUDOXDual(unittest.TestCase):
    labop_file = os.path.join(
        os.getcwd(), "test/resources/labop", "igem_ludox_dual_time_draft.ttl"
    )
    labop_format = sbol3.TURTLE

    # @unittest.skipIf(os.path.isfile(labop_file),
    #                  "skipped due to local cache")
    def test_create_dual_protocol(self):
        #############################################
        # set up the document
        print("Setting up document")
        doc = sbol3.Document()
        sbol3.set_namespace("https://bbn.com/scratch/")

        #############################################
        # Import the primitive libraries
        print("Importing libraries")
        labop.import_library("liquid_handling")
        print("... Imported liquid handling")
        labop.import_library("plate_handling")
        print("... Imported plate handling")
        labop.import_library("spectrophotometry")
        print("... Imported spectrophotometry")
        labop.import_library("sample_arrays")
        print("... Imported sample arrays")

        # create the materials to be provisioned
        ddh2o = sbol3.Component(
            "ddH2O", "https://identifiers.org/pubchem.substance:24901740"
        )
        ddh2o.name = "Water, sterile-filtered, BioReagent, suitable for cell culture"  # TODO get via tyto
        doc.add(ddh2o)

        ludox = sbol3.Component(
            "LUDOX", "https://identifiers.org/pubchem.substance:24866361"
        )
        ludox.name = (
            "LUDOX(R) CL-X colloidal silica, 45 wt. % suspension in H2O"
        )
        doc.add(ludox)

        a = self.create_protocol_a(doc, ddh2o, ludox)
        b = self.create_protocol_b(doc, ddh2o, ludox)

        # FIXME this is a quick and dirty test to see if things are working at all.
        # Testing of multiple protocols needs to be thought through in greater detail.

        constraints = []

        # protocol a starts at time 0
        constraints.append(
            labopt.startTime(a["protocol"], 0, units=tyto.OM.hour)
        )
        # protocol b starts at time hour 1
        constraints.append(
            labopt.startTime(b["protocol"], 1, units=tyto.OM.hour)
        )

        # ludox durations are 60 seconds
        constraints.append(
            labopt.duration(a["ludox"], 60, units=tyto.OM.second)
        )
        constraints.append(
            labopt.duration(b["ludox"], 60, units=tyto.OM.second)
        )

        # ddh2o durations are 60 seconds
        constraints.append(
            labopt.duration(a["ddh2o"], 60, units=tyto.OM.second)
        )
        constraints.append(
            labopt.duration(b["ddh2o"], 60, units=tyto.OM.second)
        )

        constraints.append(
            labopt.duration(a["measure"], 60, units=tyto.OM.minute)
        )
        constraints.append(
            labopt.duration(b["measure"], 60, units=tyto.OM.minute)
        )

        constraints.append(
            labopt.precedes(
                a["ludox"], [10, 15], a["ddh2o"], units=tyto.OM.hour
            )
        )
        constraints.append(
            labopt.precedes(
                b["ludox"], [10, 15], b["ddh2o"], units=tyto.OM.hour
            )
        )

        time_constraints = labopt.TimeConstraints(
            "ludox_protocol_constraints",
            constraints=[labopt.And(constraints)],
            protocols=[a["protocol"], b["protocol"]],
        )
        doc.add(time_constraints)

        ########################################
        # Validate and write the document
        print("Validating and writing protocol")
        v = doc.validate()
        assert len(v) == 0, "".join(f"\n {e}" for e in v)

        doc.write(self.labop_file, self.labop_format)
        print(f"Wrote file as {self.labop_file}")

    def create_protocol_a(self, doc, ddh2o, ludox):
        #############################################
        # Create the protocol
        print("Creating protocol")
        protocol = labop.Protocol("iGEM_LUDOX_OD_calibration_2018_A")
        protocol.name = "iGEM 2018 LUDOX OD calibration protocol A"
        protocol.description = """
With this protocol you will use LUDOX CL-X (a 45% colloidal silica suspension) as a single point reference to
obtain a conversion factor to transform absorbance (OD600) data from your plate reader into a comparable
OD600 measurement as would be obtained in a spectrophotometer. This conversion is necessary because plate
reader measurements of absorbance are volume dependent; the depth of the fluid in the well defines the path
length of the light passing through the sample, which can vary slightly from well to well. In a standard
spectrophotometer, the path length is fixed and is defined by the width of the cuvette, which is constant.
Therefore this conversion calculation can transform OD600 measurements from a plate reader (i.e. absorbance
at 600 nm, the basic output of most instruments) into comparable OD600 measurements. The LUDOX solution
is only weakly scattering and so will give a low absorbance value.
        """
        doc.add(protocol)
        # actual steps of the protocol
        # get a plate
        plate = protocol.primitive_step(
            "EmptyContainer",
            specification=tyto.NCIT.get_uri_by_term("Microplate"),
        )  # replace with container ontology

        # put ludox and water in selected wells
        c_ddh2o = protocol.primitive_step(
            "PlateCoordinates",
            source=plate.output_pin("samples"),
            coordinates="A1:D1",
        )
        provision_ludox = protocol.primitive_step(
            "Provision",
            resource=ludox,
            destination=c_ddh2o.output_pin("samples"),
            amount=sbol3.Measure(100, tyto.OM.microliter),
        )

        c_ludox = protocol.primitive_step(
            "PlateCoordinates",
            source=plate.output_pin("samples"),
            coordinates="A2:D2",
        )
        provision_ddh2o = protocol.primitive_step(
            "Provision",
            resource=ddh2o,
            destination=c_ludox.output_pin("samples"),
            amount=sbol3.Measure(100, tyto.OM.microliter),
        )

        # measure the absorbance
        c_measure = protocol.primitive_step(
            "PlateCoordinates",
            source=plate.output_pin("samples"),
            coordinates="A1:D2",
        )
        measure = protocol.primitive_step(
            "MeasureAbsorbance",
            samples=c_measure.output_pin("samples"),
            wavelength=sbol3.Measure(600, tyto.OM.nanometer),
        )

        protocol.add_output("absorbance", measure.output_pin("measurements"))

        return {
            "protocol": protocol,
            "ludox": provision_ludox,
            "ddh2o": provision_ddh2o,
            "measure": measure,
        }

    def create_protocol_b(self, doc, ddh2o, ludox):
        #############################################
        # Create the protocol
        print("Creating protocol")
        protocol = labop.Protocol("iGEM_LUDOX_OD_calibration_2018_B")
        protocol.name = "iGEM 2018 LUDOX OD calibration protocol B"
        protocol.description = """
With this protocol you will use LUDOX CL-X (a 45% colloidal silica suspension) as a single point reference to
obtain a conversion factor to transform absorbance (OD600) data from your plate reader into a comparable
OD600 measurement as would be obtained in a spectrophotometer. This conversion is necessary because plate
reader measurements of absorbance are volume dependent; the depth of the fluid in the well defines the path
length of the light passing through the sample, which can vary slightly from well to well. In a standard
spectrophotometer, the path length is fixed and is defined by the width of the cuvette, which is constant.
Therefore this conversion calculation can transform OD600 measurements from a plate reader (i.e. absorbance
at 600 nm, the basic output of most instruments) into comparable OD600 measurements. The LUDOX solution
is only weakly scattering and so will give a low absorbance value.
        """
        doc.add(protocol)

        # actual steps of the protocol
        # get a plate
        plate = protocol.primitive_step(
            "EmptyContainer",
            specification=tyto.NCIT.get_uri_by_term("Microplate"),
        )  # replace with container ontology

        # put ludox and water in selected wells
        c_ddh2o = protocol.primitive_step(
            "PlateCoordinates",
            source=plate.output_pin("samples"),
            coordinates="A1:D1",
        )
        provision_ludox = protocol.primitive_step(
            "Provision",
            resource=ludox,
            destination=c_ddh2o.output_pin("samples"),
            amount=sbol3.Measure(100, tyto.OM.microliter),
        )

        c_ludox = protocol.primitive_step(
            "PlateCoordinates",
            source=plate.output_pin("samples"),
            coordinates="A2:D2",
        )
        provision_ddh2o = protocol.primitive_step(
            "Provision",
            resource=ddh2o,
            destination=c_ludox.output_pin("samples"),
            amount=sbol3.Measure(100, tyto.OM.microliter),
        )

        # measure the absorbance
        c_measure = protocol.primitive_step(
            "PlateCoordinates",
            source=plate.output_pin("samples"),
            coordinates="A1:D2",
        )
        measure = protocol.primitive_step(
            "MeasureAbsorbance",
            samples=c_measure.output_pin("samples"),
            wavelength=sbol3.Measure(600, tyto.OM.nanometer),
        )

        protocol.add_output("absorbance", measure.output_pin("measurements"))

        return {
            "protocol": protocol,
            "ludox": provision_ludox,
            "ddh2o": provision_ddh2o,
            "measure": measure,
        }


if __name__ == "__main__":
    unittest.main()

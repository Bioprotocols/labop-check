import os
import tempfile
import unittest
import filecmp
import sbol3
import labop
import tyto


class TestLUDOX(unittest.TestCase):
    labop_file = os.path.join(
        os.getcwd(), "test/resources/labop", "igem_ludox_draft.ttl"
    )
    labop_format = sbol3.TURTLE

    # @unittest.skipIf(os.path.isfile(labop_file),
    #                  "skipped due to local cache")
    def test_create_protocol(self):
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

        #############################################
        # Create the protocol
        print("Creating protocol")
        protocol = labop.Protocol("iGEM_LUDOX_OD_calibration_2018")
        protocol.name = "iGEM 2018 LUDOX OD calibration protocol"
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
        protocol.primitive_step(
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
        protocol.primitive_step(
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

        ########################################
        # Validate and write the document
        print("Validating and writing protocol")
        v = doc.validate()
        assert len(v) == 0, "".join(f"\n {e}" for e in v)

        doc.write(self.labop_file, self.labop_format)
        print(f"Wrote file as {self.labop_file}")


if __name__ == "__main__":
    unittest.main()

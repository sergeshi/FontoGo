import unittest
from fontogo_core.model import Document, Glyph, Contour, Segment, UndoHistory, transform_contour

class ModelTests(unittest.TestCase):
    def test_json_roundtrip(self):
        d=Document(glyphs={"A":Glyph("A",codepoints=[65],contours=[Contour((0,0),[Segment("line",(100,0)),Segment("line",(50,100))])])},cmap={65:"A"})
        d.validate()
        clone=Document.from_dict(d.to_dict())
        self.assertEqual(clone.glyphs["A"].contours[0].segments[1].end,(50,100))
    def test_transform(self):
        c=Contour((1,2),[Segment("cubic",(5,6),(2,3),(4,5))])
        moved=transform_contour(c,(1,0,0,1,10,-2))
        self.assertEqual(moved.start,(11,0)); self.assertEqual(moved.segments[0].control1,(12,1))
    def test_undo_redo(self):
        h=UndoHistory({"x":1}); h.commit({"x":2})
        self.assertEqual(h.undo(),{"x":1}); self.assertEqual(h.redo(),{"x":2})
    def test_reject_missing_cmap_glyph(self):
        d=Document(cmap={65:"missing"})
        with self.assertRaises(ValueError): d.validate()

if __name__ == "__main__": unittest.main()

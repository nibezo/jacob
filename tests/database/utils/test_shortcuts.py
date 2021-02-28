from pyshould import it

from jacob.database.models import Chat
from jacob.database.utils import admin, shortcuts


class TestShortcuts:
    def test_get_list_of_calling_students(self):

        test_admin_id = 1

        res = shortcuts.get_list_of_calling_students(test_admin_id)

        it(res).should.be_equal([1, 2, 3])

    def test_pop_student_from_calling_list(self):

        test_admin_id = 1
        test_student_id = 3

        res = shortcuts.pop_student_from_calling_list(test_admin_id, test_student_id)
        data = list(map(int, res.selected_students.split(",")))
        it(data).should.be_equal([1, 2])

    def test_add_student_to_calling_list(self):

        test_admin_id = 1
        test_student_id = 3

        res = shortcuts.add_student_to_calling_list(test_admin_id, test_student_id)
        data = list(map(int, res.selected_students.split(",")))
        it(data).should.be_equal([1, 2, 3])

    def test_get_active_chat(self):

        test_admin_id = 1
        test_chat = Chat.get(id=2)

        res = shortcuts.get_active_chat(test_admin_id)

        it(res).should.be_equal(test_chat)

    def test_invert_names_usage(self):

        test_admin_id = 1
        test_store = admin.get_admin_storage(test_admin_id)

        shortcuts.invert_names_usage(test_admin_id)
        res = shortcuts.invert_names_usage(test_admin_id)

        it(res.names_usage).should.be_equal(test_store.names_usage)

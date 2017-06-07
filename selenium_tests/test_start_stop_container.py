# -*- coding: utf-8 -*-
from selenium_tests.selenium_test_base import SeleniumTestBase
from selenium.webdriver.common.by import By


class TestContainerInteraction(SeleniumTestBase):
    def test_start_stop_container(self):
        with self.logged_in():
            self.wait_until_application_list_loaded()

            self.select_application()
            self.start_selected_application()
            self.wait_until_selected_application_running()

            self.open_application_settings()
            self.stop_selected_application()
            self.wait_until_selected_application_stopped()

    def test_start_stop_two_containers(self):
        with self.logged_in():
            self.wait_until_application_list_loaded()

            self.select_application(0)
            self.start_selected_application()
            self.wait_until_selected_application_running()

            self.select_application(1)
            self.start_selected_application()
            self.wait_until_selected_application_running()

            self.select_application(0)
            self.open_application_settings()
            self.stop_selected_application()
            self.wait_until_selected_application_stopped()

            self.select_application(1)
            self.open_application_settings()
            self.stop_selected_application()
            self.wait_until_selected_application_stopped()

    def test_focus(self):
        with self.running_container():
            iframe = self.wait_until_element_visible(By.TAG_NAME, "iframe")
            self.assertEqual(iframe, self.driver.switch_to.active_element)

            self.type_text_in_element_located(By.ID, "search-input", "")

            self.assertNotEqual(iframe, self.driver.switch_to.active_element)

            self.select_application()

            self.assertEqual(iframe, self.driver.switch_to.active_element)

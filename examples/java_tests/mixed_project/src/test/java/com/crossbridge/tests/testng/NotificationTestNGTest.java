package com.crossbridge.tests.testng;

import org.testng.annotations.*;
import static org.testng.Assert.*;

/**
 * TestNG test in a mixed framework project.
 */
public class NotificationTestNGTest {

    @Test(groups = {"smoke", "notification"})
    public void testEmailNotification() {
        String recipient = "user@example.com";
        String subject = "Test Subject";
        String body = "Test Body";
        
        boolean result = sendEmail(recipient, subject, body);
        
        assertTrue(result, "Email notification should be sent successfully");
    }

    @Test(groups = {"regression", "notification"})
    public void testSmsNotification() {
        String phoneNumber = "+1234567890";
        String message = "Test SMS";
        
        boolean result = sendSms(phoneNumber, message);
        
        assertTrue(result, "SMS notification should be sent successfully");
    }

    @Test(groups = {"notification"}, priority = 1)
    public void testPushNotification() {
        String deviceId = "DEVICE123";
        String message = "Test Push";
        
        boolean result = sendPush(deviceId, message);
        
        assertTrue(result, "Push notification should be sent successfully");
    }

    @DataProvider(name = "notificationData")
    public Object[][] createNotificationData() {
        return new Object[][] {
            {"email", "user@example.com", true},
            {"sms", "+1234567890", true},
            {"push", "DEVICE123", true},
            {"email", "", false}
        };
    }

    @Test(dataProvider = "notificationData", groups = {"notification", "data-driven"})
    public void testMultipleNotificationTypes(String type, String recipient, boolean shouldSucceed) {
        boolean result = sendNotification(type, recipient);
        
        assertEquals(result, shouldSucceed,
                    String.format("Notification %s to %s should %s",
                                type, recipient, shouldSucceed ? "succeed" : "fail"));
    }

    private boolean sendEmail(String recipient, String subject, String body) {
        return recipient != null && !recipient.isEmpty() && recipient.contains("@");
    }

    private boolean sendSms(String phoneNumber, String message) {
        return phoneNumber != null && phoneNumber.startsWith("+");
    }

    private boolean sendPush(String deviceId, String message) {
        return deviceId != null && !deviceId.isEmpty();
    }

    private boolean sendNotification(String type, String recipient) {
        if (recipient == null || recipient.isEmpty()) {
            return false;
        }
        switch (type) {
            case "email": return recipient.contains("@");
            case "sms": return recipient.startsWith("+");
            case "push": return true;
            default: return false;
        }
    }
}

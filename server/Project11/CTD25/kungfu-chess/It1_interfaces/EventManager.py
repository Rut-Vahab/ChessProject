from typing import Dict, List, Callable, Any


class EventManager:
    """
    מנהל אירועים פשוט המממש את דפוס Publish/Subscribe
    """
    
    def __init__(self):
        # מילון שמחזיק רשימה של פונקציות לכל סוג אירוע
        self.subscribers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        """
        רישום למנוי על אירוע מסוים
        
        Args:
            event_type: סוג האירוע (למשל "piece_captured", "move_made")
            callback: הפונקציה שתיקרא כשהאירוע יקרה
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]):
        """
        ביטול מנוי על אירוע
        """
        if event_type in self.subscribers:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                print(f"Unsubscribed from event: {event_type}")
    
    def publish(self, event_type: str, event_data: Any = None):
        """
        פרסום אירוע לכל המנויים
        
        Args:
            event_type: סוג האירוע
            event_data: מידע נוסף על האירוע
        """
        if event_type in self.subscribers:
            print(f"Publishing event: {event_type} to {len(self.subscribers[event_type])} subscribers")
            for callback in self.subscribers[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    print(f"Error in event callback for {event_type}: {e}")
        else:
            print(f"No subscribers for event: {event_type}")


# דוגמה פשוטה לבדיקה
if __name__ == "__main__":
    # יצירת מנהל אירועים
    event_manager = EventManager()
    
    # פונקציה שתקבל הודעות
    def on_test_event(data):
        print(f"Received event with data: {data}")
    
    # רישום למנוי
    event_manager.subscribe("test", on_test_event)
    
    # פרסום אירוע
    event_manager.publish("test", "Hello World!")

#import <UIKit/UIKit.h>


@interface tcDirList : NSObject {
	NSString * path;
}
- (id) initWithPath: (NSString *) initPath;
- (NSString *)firstFile;
- (NSString *)fileAfter:(NSString*) current;
- (NSString *)fileBefore:(NSString*) current;
- (NSString *)fileNextTo:(NSString*) current before:(BOOL) getBeforeFile;
@end
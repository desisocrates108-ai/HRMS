import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import API from '@/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { ScrollArea } from '@/components/ui/scroll-area';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import {
  MessageSquare, Plus, Send, ArrowLeft, Settings, UserPlus,
  Paperclip, MoreVertical, Pencil, Trash2, FileText, Image, Check, X, Users as UsersIcon, Eye, Shield
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ChatPage() {
  const { user } = useAuth();
  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [chatDetail, setChatDetail] = useState(null);
  const [messages, setMessages] = useState([]);
  const [msgText, setMsgText] = useState('');
  const [loading, setLoading] = useState(true);
  const [newChatOpen, setNewChatOpen] = useState(false);
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [eligibleUsers, setEligibleUsers] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [groupName, setGroupName] = useState('');
  const [addForm, setAddForm] = useState({ user_id: '', permission: 'can_reply', show_history: true });
  const [editingMsg, setEditingMsg] = useState(null);
  const [editText, setEditText] = useState('');
  const messagesEndRef = useRef(null);
  const pollRef = useRef(null);
  const lastPollTime = useRef(new Date().toISOString());
  const fileInputRef = useRef(null);

  // Fetch chats on mount
  useEffect(() => {
    fetchChats();
    fetchEligibleUsers();
  }, []);

  // Poll for new messages
  useEffect(() => {
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await API.get(`/chat/poll?since=${lastPollTime.current}`);
        if (data.messages && data.messages.length > 0) {
          lastPollTime.current = data.messages[data.messages.length - 1].created_at;
          // Update messages if in active chat
          setMessages(prev => {
            const newMsgs = data.messages.filter(m => m.chat_id === activeChat);
            if (newMsgs.length === 0) return prev;
            const existingIds = new Set(prev.map(m => m.id));
            const unique = newMsgs.filter(m => !existingIds.has(m.id));
            return [...prev, ...unique];
          });
          // Refresh chat list for updated last messages
          fetchChats();
        }
      } catch {}
    }, 2500);
    return () => clearInterval(pollRef.current);
  }, [activeChat]);

  // Scroll to bottom when new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchChats = async () => {
    try {
      const { data } = await API.get('/chat');
      setChats(data);
    } catch {}
    finally { setLoading(false); }
  };

  const fetchEligibleUsers = async () => {
    try {
      const { data } = await API.get('/chat/eligible-users');
      setEligibleUsers(data);
    } catch {}
  };

  const openChat = async (chatId) => {
    setActiveChat(chatId);
    try {
      const [detailRes, msgsRes] = await Promise.all([
        API.get(`/chat/${chatId}`),
        API.get(`/chat/${chatId}/messages`)
      ]);
      setChatDetail(detailRes.data);
      setMessages(msgsRes.data);
      if (msgsRes.data.length > 0) {
        lastPollTime.current = msgsRes.data[msgsRes.data.length - 1].created_at;
      }
    } catch (err) { toast.error('Failed to load chat'); }
  };

  const handleSend = async () => {
    if (!msgText.trim() || !activeChat) return;
    try {
      const { data } = await API.post(`/chat/${activeChat}/messages`, { text: msgText });
      setMessages(prev => [...prev, data]);
      setMsgText('');
      fetchChats();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to send'); }
  };

  const handleCreateChat = async () => {
    if (selectedUsers.length === 0) return;
    try {
      const payload = { user_ids: selectedUsers, name: selectedUsers.length > 1 ? groupName || null : null };
      const { data } = await API.post('/chat', payload);
      setNewChatOpen(false);
      setSelectedUsers([]);
      setGroupName('');
      fetchChats();
      openChat(data.id);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create chat'); }
  };

  const handleAddMember = async () => {
    if (!addForm.user_id) return;
    try {
      await API.post(`/chat/${activeChat}/members`, addForm);
      toast.success('Member added');
      setAddMemberOpen(false);
      setAddForm({ user_id: '', permission: 'can_reply', show_history: true });
      openChat(activeChat);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to add member'); }
  };

  const handleUpdatePermission = async (userId, permission) => {
    try {
      await API.put(`/chat/${activeChat}/members/${userId}`, { permission });
      toast.success('Permission updated');
      openChat(activeChat);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const handleEditMessage = async () => {
    if (!editingMsg || !editText.trim()) return;
    try {
      const { data } = await API.put(`/chat/${activeChat}/messages/${editingMsg}`, { text: editText });
      setMessages(prev => prev.map(m => m.id === editingMsg ? data : m));
      setEditingMsg(null);
      setEditText('');
    } catch (err) { toast.error(err.response?.data?.detail || 'Cannot edit'); }
  };

  const handleDeleteMessage = async (msgId) => {
    try {
      await API.delete(`/chat/${activeChat}/messages/${msgId}`);
      setMessages(prev => prev.map(m => m.id === msgId ? { ...m, is_deleted: true, text: 'This message was deleted' } : m));
    } catch (err) { toast.error(err.response?.data?.detail || 'Cannot delete'); }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const { data } = await API.post(`/chat/${activeChat}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      // Send message with file
      const msg = await API.post(`/chat/${activeChat}/messages`, {
        text: file.name, file_url: data.file_url, file_name: data.file_name
      });
      setMessages(prev => [...prev, msg.data]);
      fetchChats();
    } catch (err) { toast.error('Upload failed'); }
  };

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  const showList = !activeChat || !isMobile;
  const showThread = activeChat || !isMobile;
  const isViewOnly = chatDetail?.my_permission === 'view_only';

  const chatMembers = chatDetail?.members || [];
  const nonMembers = eligibleUsers.filter(u => !chatMembers.find(m => m.user_id === u.id));

  return (
    <div className="flex h-[calc(100vh-6rem)] md:h-[calc(100vh-4rem)] -m-4 md:-m-6 lg:-m-8" data-testid="chat-page">
      {/* Chat List Panel */}
      {showList && (
        <div className={`${activeChat && !isMobile ? 'w-80 border-r border-slate-200' : 'w-full'} flex flex-col bg-white`}>
          <div className="p-3 border-b border-slate-200 flex items-center justify-between">
            <h2 className="font-heading font-semibold text-slate-900">Chats</h2>
            <Button size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={() => setNewChatOpen(true)} data-testid="new-chat-button">
              <Plus className="w-4 h-4 mr-1" /> New
            </Button>
          </div>
          <ScrollArea className="flex-1">
            {chats.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-sm">No chats yet. Start a conversation!</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {chats.map(chat => (
                  <div
                    key={chat.id}
                    className={`p-3 cursor-pointer hover:bg-slate-50 transition-colors ${activeChat === chat.id ? 'bg-blue-50' : ''}`}
                    onClick={() => openChat(chat.id)}
                    data-testid={`chat-item-${chat.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                        {chat.type === 'group' ? <UsersIcon className="w-5 h-5 text-blue-700" /> : <MessageSquare className="w-5 h-5 text-blue-700" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-slate-900 truncate">{chat.display_name}</p>
                          {chat.last_message?.timestamp && (
                            <span className="text-xs text-slate-400 flex-shrink-0">{new Date(chat.last_message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          )}
                        </div>
                        {chat.last_message && (
                          <p className="text-xs text-slate-500 truncate mt-0.5">
                            {chat.last_message.type === 'system' ? chat.last_message.text : `${chat.last_message.sender_name}: ${chat.last_message.text}`}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
      )}

      {/* Chat Thread Panel */}
      {showThread && activeChat && (
        <div className="flex-1 flex flex-col bg-slate-50">
          {/* Header */}
          <div className="p-3 bg-white border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isMobile && (
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setActiveChat(null)} data-testid="back-to-chats">
                  <ArrowLeft className="w-4 h-4" />
                </Button>
              )}
              <div>
                <p className="font-medium text-sm text-slate-900">{chatDetail?.display_name}</p>
                <p className="text-xs text-slate-500">{chatMembers.length} members {isViewOnly && <Badge variant="outline" className="text-xs ml-1">View Only</Badge>}</p>
              </div>
            </div>
            <div className="flex gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setAddMemberOpen(true)} data-testid="add-member-btn">
                <UserPlus className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSettingsOpen(true)} data-testid="chat-settings-btn">
                <Settings className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 p-3">
            <div className="space-y-2 max-w-2xl mx-auto">
              {messages.map(msg => {
                const isMe = msg.sender_id === user?.id;
                const isSystem = msg.type === 'system';
                if (isSystem) {
                  return (
                    <div key={msg.id} className="text-center py-1">
                      <span className="text-xs text-slate-400 bg-slate-100 px-3 py-1 rounded-full">{msg.text}</span>
                    </div>
                  );
                }
                const canEdit = isMe && !msg.is_deleted && !msg.is_edited && new Date() - new Date(msg.created_at) < EDIT_TIME_LIMIT_MINUTES * 60 * 1000;
                const canDelete = isMe || user?.role === 'CEO';
                return (
                  <div key={msg.id} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[75%] ${isMe ? 'bg-blue-700 text-white' : 'bg-white border border-slate-200 text-slate-900'} rounded-2xl px-3 py-2 ${isMe ? 'rounded-br-md' : 'rounded-bl-md'} group relative`}>
                      {!isMe && <p className="text-xs font-medium mb-0.5" style={{ color: isMe ? '#93C5FD' : '#1D4ED8' }}>{msg.sender_name}</p>}
                      {msg.is_deleted ? (
                        <p className="text-sm italic opacity-60">This message was deleted</p>
                      ) : msg.type === 'file' && msg.file_url ? (
                        <div>
                          <a href={`${BACKEND_URL}${msg.file_url}`} target="_blank" rel="noopener noreferrer" className={`flex items-center gap-2 text-sm ${isMe ? 'text-blue-100 underline' : 'text-blue-600 underline'}`}>
                            {msg.file_url?.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? <Image className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                            {msg.file_name || 'File'}
                          </a>
                          {msg.text && msg.text !== msg.file_name && <p className="text-sm mt-1">{msg.text}</p>}
                        </div>
                      ) : (
                        <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                      )}
                      <div className="flex items-center justify-end gap-1 mt-0.5">
                        {msg.is_edited && <span className="text-xs opacity-50">edited</span>}
                        <span className={`text-xs ${isMe ? 'text-blue-200' : 'text-slate-400'}`}>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      {/* Context menu */}
                      {!msg.is_deleted && (canEdit || canDelete) && (
                        <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className={`h-6 w-6 ${isMe ? 'text-blue-200 hover:text-white' : 'text-slate-400'}`}>
                                <MoreVertical className="w-3 h-3" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent>
                              {canEdit && <DropdownMenuItem onClick={() => { setEditingMsg(msg.id); setEditText(msg.text); }}><Pencil className="w-3 h-3 mr-2" /> Edit</DropdownMenuItem>}
                              {canDelete && !msg.is_deleted && <DropdownMenuItem onClick={() => handleDeleteMessage(msg.id)} className="text-red-600"><Trash2 className="w-3 h-3 mr-2" /> Delete</DropdownMenuItem>}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Edit bar */}
          {editingMsg && (
            <div className="px-3 py-2 bg-amber-50 border-t border-amber-200 flex items-center gap-2">
              <Pencil className="w-4 h-4 text-amber-600" />
              <Input value={editText} onChange={e => setEditText(e.target.value)} className="flex-1 h-8" onKeyDown={e => e.key === 'Enter' && handleEditMessage()} />
              <Button size="sm" className="h-8 bg-amber-600 hover:bg-amber-700" onClick={handleEditMessage}><Check className="w-3 h-3" /></Button>
              <Button size="sm" variant="ghost" className="h-8" onClick={() => { setEditingMsg(null); setEditText(''); }}><X className="w-3 h-3" /></Button>
            </div>
          )}

          {/* Input */}
          {!isViewOnly ? (
            <div className="p-3 bg-white border-t border-slate-200 flex items-center gap-2">
              <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
              <Button variant="ghost" size="icon" className="h-10 w-10 flex-shrink-0" onClick={() => fileInputRef.current?.click()} data-testid="file-upload-btn">
                <Paperclip className="w-4 h-4 text-slate-500" />
              </Button>
              <Input
                value={msgText}
                onChange={e => setMsgText(e.target.value)}
                placeholder="Type a message..."
                className="flex-1 h-10"
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
                data-testid="message-input"
              />
              <Button className="h-10 w-10 bg-blue-700 hover:bg-blue-800 p-0 flex-shrink-0" onClick={handleSend} data-testid="send-message-btn">
                <Send className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <div className="p-3 bg-slate-100 border-t text-center text-sm text-slate-500">
              <Eye className="w-4 h-4 inline mr-1" /> View-only access. You cannot send messages.
            </div>
          )}
        </div>
      )}

      {/* Empty state for desktop */}
      {!activeChat && !isMobile && (
        <div className="flex-1 flex items-center justify-center bg-slate-50">
          <div className="text-center text-slate-400">
            <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">Select a chat or start a new conversation</p>
          </div>
        </div>
      )}

      {/* New Chat Dialog */}
      <Dialog open={newChatOpen} onOpenChange={setNewChatOpen}>
        <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto"><DialogDescription className="sr-only">Start a new chat</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading">New Chat</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-xs text-slate-500">Select users to chat with. Multiple users creates a group chat.</p>
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {eligibleUsers.map(u => (
                <div key={u.id} className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-all ${selectedUsers.includes(u.id) ? 'bg-blue-50 border border-blue-200' : 'hover:bg-slate-50 border border-transparent'}`}
                  onClick={() => setSelectedUsers(prev => prev.includes(u.id) ? prev.filter(id => id !== u.id) : [...prev, u.id])}>
                  <div><p className="text-sm font-medium text-slate-900">{u.name}</p><p className="text-xs text-slate-500">{u.role}</p></div>
                  {selectedUsers.includes(u.id) && <Check className="w-4 h-4 text-blue-700" />}
                </div>
              ))}
            </div>
            {selectedUsers.length > 1 && (
              <div><Label className="text-xs font-semibold uppercase text-slate-500">Group Name</Label><Input value={groupName} onChange={e => setGroupName(e.target.value)} placeholder="Name this group..." className="mt-1" /></div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setNewChatOpen(false); setSelectedUsers([]); }}>Cancel</Button>
            <Button className="bg-blue-700 hover:bg-blue-800" onClick={handleCreateChat} disabled={selectedUsers.length === 0} data-testid="create-chat-btn">
              {selectedUsers.length > 1 ? 'Create Group' : 'Start Chat'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Member Dialog */}
      <Dialog open={addMemberOpen} onOpenChange={setAddMemberOpen}>
        <DialogContent className="max-w-md"><DialogDescription className="sr-only">Add a member to this chat</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading">Add Member</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-xs font-semibold uppercase text-slate-500">Select User</Label>
              <Select value={addForm.user_id} onValueChange={v => setAddForm({...addForm, user_id: v})}>
                <SelectTrigger className="mt-1" data-testid="add-member-select"><SelectValue placeholder="Choose user" /></SelectTrigger>
                <SelectContent>{nonMembers.map(u => <SelectItem key={u.id} value={u.id}>{u.name} ({u.role})</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase text-slate-500">Permission</Label>
              <Select value={addForm.permission} onValueChange={v => setAddForm({...addForm, permission: v})}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="can_reply">Can Reply (send messages)</SelectItem>
                  <SelectItem value="view_only">View Only (read-only)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold uppercase text-slate-500">Chat History</Label>
              <div className="flex items-center gap-3 mt-1">
                <Switch checked={addForm.show_history} onCheckedChange={v => setAddForm({...addForm, show_history: v})} />
                <span className="text-sm text-slate-700">{addForm.show_history ? 'Show old messages' : 'Show only new messages'}</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddMemberOpen(false)}>Cancel</Button>
            <Button className="bg-blue-700 hover:bg-blue-800" onClick={handleAddMember} data-testid="confirm-add-member">Add Member</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto"><DialogDescription className="sr-only">Chat settings and members</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading">Chat Settings</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase text-slate-500">Members ({chatMembers.length})</p>
            <div className="space-y-2">
              {chatMembers.map(m => (
                <div key={m.user_id} className="flex items-center justify-between p-2 rounded-lg border border-slate-200">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{m.user_name}</p>
                    <p className="text-xs text-slate-500">{m.user_role}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Select value={m.permission} onValueChange={v => handleUpdatePermission(m.user_id, v)}>
                      <SelectTrigger className="w-28 h-7 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="can_reply">Can Reply</SelectItem>
                        <SelectItem value="view_only">View Only</SelectItem>
                      </SelectContent>
                    </Select>
                    {!m.show_history && <Badge variant="outline" className="text-xs">New only</Badge>}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setSettingsOpen(false)}>Close</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const EDIT_TIME_LIMIT_MINUTES = 15;

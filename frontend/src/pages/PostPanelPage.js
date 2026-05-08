import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import API from '@/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Image, Upload, CheckCircle, Clock, Send, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PostPanelPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const isDesigner = user?.role === 'Graphic Designer';
  const isHR = ['HR', 'CEO', 'Super Admin', 'Sr HR', 'Jr HR'].includes(user?.role);

  const [requests, setRequests] = useState([]);
  const [posts, setPosts] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [requestOpen, setRequestOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [actionOpen, setActionOpen] = useState(false);
  const [selectedReq, setSelectedReq] = useState(null);
  const [selectedPost, setSelectedPost] = useState(null);
  const [reqForm, setReqForm] = useState({ job_id: '', notes: '' });
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadNotes, setUploadNotes] = useState('');
  const [actionForm, setActionForm] = useState({ action: 'job_portal', assigned_to: '' });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [reqRes, postRes, jobRes, userRes] = await Promise.all([
        API.get('/posts/requests'), API.get('/posts'), API.get('/jobs'), API.get('/users')
      ]);
      setRequests(reqRes.data);
      setPosts(postRes.data);
      setJobs(jobRes.data);
      setUsers(userRes.data);
    } catch {} finally { setLoading(false); }
  };

  const handleRequest = async () => {
    try {
      await API.post('/posts/request', { job_id: reqForm.job_id, notes: reqForm.notes || null });
      toast.success('Post request sent to designer');
      setRequestOpen(false);
      setReqForm({ job_id: '', notes: '' });
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const handleUpload = async () => {
    if (!uploadFile || !selectedReq) return;
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      const { data: fileData } = await API.post('/posts/upload-file', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      await API.post('/posts/upload', { request_id: selectedReq.id, file_url: fileData.file_url, file_name: fileData.file_name, notes: uploadNotes || null });
      toast.success('Post uploaded!');
      setUploadOpen(false);
      setUploadFile(null);
      setUploadNotes('');
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Upload failed'); }
  };

  const handleAction = async () => {
    if (!selectedPost) return;
    try {
      const mktgCoord = users.find(u => u.role === 'Marketing Coordinator');
      await API.put(`/posts/${selectedPost.id}/action`, { action: actionForm.action, assigned_to: actionForm.action === 'meta_ads' ? (actionForm.assigned_to || mktgCoord?.id) : null });
      toast.success(`Sent to ${actionForm.action.replace('_', ' ')}`);
      setActionOpen(false);
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  const pendingReqs = requests.filter(r => r.status === 'pending');
  const pendingReviews = posts.filter(p => p.review_status === 'pending');

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-500">Loading...</div>;

  return (
    <div className="space-y-4" data-testid="post-panel-page">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={() => nav(-1)}><ArrowLeft className="w-4 h-4" /></Button>
        <div><h1 className="text-xl md:text-2xl font-heading font-semibold text-slate-900">Post Panel</h1><p className="text-sm text-slate-500">Design requests and uploads</p></div>
      </div>

      <div className="flex gap-2 flex-wrap">
        {isHR && <Button size="sm" className="bg-blue-700 hover:bg-blue-800" onClick={() => setRequestOpen(true)} data-testid="request-post-btn"><Send className="w-3 h-3 mr-1" />Request Design</Button>}
      </div>

      <Tabs defaultValue={isDesigner ? 'requests' : 'posts'}>
        <TabsList className="grid grid-cols-2 w-full md:w-80">
          <TabsTrigger value="requests">Requests ({pendingReqs.length} pending)</TabsTrigger>
          <TabsTrigger value="posts">Uploads ({posts.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="requests" className="mt-3 space-y-2">
          {requests.length === 0 ? <p className="text-sm text-slate-500 py-8 text-center">No requests yet</p> : requests.map(r => (
            <Card key={r.id} className="border-slate-200 shadow-none">
              <CardContent className="p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm text-slate-900">{r.role} - {r.job_info}</p>
                    <p className="text-xs text-slate-500">By: {r.requested_by_name} | {new Date(r.created_at).toLocaleDateString()}</p>
                    {r.notes && <p className="text-xs text-slate-400 mt-1">{r.notes}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={r.status === 'completed' ? 'bg-emerald-100 text-emerald-700 border-0' : 'bg-amber-100 text-amber-700 border-0'}>{r.status}</Badge>
                    {isDesigner && r.status === 'pending' && (
                      <Button size="sm" variant="outline" onClick={() => { setSelectedReq(r); setUploadOpen(true); }} data-testid={`upload-post-${r.id}`}>
                        <Upload className="w-3 h-3 mr-1" />Upload
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="posts" className="mt-3 space-y-2">
          {posts.length === 0 ? <p className="text-sm text-slate-500 py-8 text-center">No posts uploaded yet</p> : posts.map(p => (
            <Card key={p.id} className="border-slate-200 shadow-none">
              <CardContent className="p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm text-slate-900">{p.role} - {p.job_info}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <a href={`${BACKEND_URL}${p.file_url}`} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 underline flex items-center gap-1"><Image className="w-3 h-3" />{p.file_name}</a>
                      <span className="text-xs text-slate-400">by {p.uploaded_by_name}</span>
                      <span className="text-xs text-slate-400">req: {p.requested_by_name}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={p.review_status === 'approved' ? 'bg-emerald-100 text-emerald-700 border-0' : 'bg-amber-100 text-amber-700 border-0'}>{p.review_status}</Badge>
                    {p.action !== 'none' && <Badge variant="outline" className="text-xs">{p.action?.replace('_', ' ')}</Badge>}
                    {isHR && p.review_status === 'pending' && (
                      <Button size="sm" variant="outline" onClick={() => { setSelectedPost(p); setActionOpen(true); }} data-testid={`action-post-${p.id}`}>Action</Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>

      {/* Request Dialog */}
      <Dialog open={requestOpen} onOpenChange={setRequestOpen}>
        <DialogContent className="max-w-md"><DialogDescription className="sr-only">Request a design</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading">Request Post Design</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label className="text-xs font-semibold uppercase text-slate-500">Job</Label>
              <Select value={reqForm.job_id} onValueChange={v => setReqForm({...reqForm, job_id: v})}><SelectTrigger className="mt-1"><SelectValue placeholder="Select job" /></SelectTrigger><SelectContent>{jobs.filter(j => j.status === 'open').map(j => <SelectItem key={j.id} value={j.id}>{j.role} - {j.location}</SelectItem>)}</SelectContent></Select></div>
            <div><Label className="text-xs font-semibold uppercase text-slate-500">Notes</Label><Input value={reqForm.notes} onChange={e => setReqForm({...reqForm, notes: e.target.value})} placeholder="Any specific instructions..." className="mt-1" /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setRequestOpen(false)}>Cancel</Button><Button className="bg-blue-700 hover:bg-blue-800" onClick={handleRequest}>Send Request</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Dialog */}
      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent className="max-w-md"><DialogDescription className="sr-only">Upload design</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading">Upload Design for: {selectedReq?.role}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label className="text-xs font-semibold uppercase text-slate-500">Design File</Label><Input type="file" onChange={e => setUploadFile(e.target.files?.[0])} className="mt-1" data-testid="design-file-input" /></div>
            <div><Label className="text-xs font-semibold uppercase text-slate-500">Notes</Label><Input value={uploadNotes} onChange={e => setUploadNotes(e.target.value)} className="mt-1" /></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setUploadOpen(false)}>Cancel</Button><Button className="bg-blue-700 hover:bg-blue-800" onClick={handleUpload} data-testid="confirm-upload">Upload</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Action Dialog */}
      <Dialog open={actionOpen} onOpenChange={setActionOpen}>
        <DialogContent className="max-w-md"><DialogDescription className="sr-only">Decide post action</DialogDescription>
          <DialogHeader><DialogTitle className="font-heading">Review Post: {selectedPost?.role}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label className="text-xs font-semibold uppercase text-slate-500">Action</Label>
              <Select value={actionForm.action} onValueChange={v => setActionForm({...actionForm, action: v})}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="job_portal">Upload to Job Portal</SelectItem><SelectItem value="meta_ads">Assign to Marketing for Meta Ads</SelectItem></SelectContent></Select></div>
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setActionOpen(false)}>Cancel</Button><Button className="bg-blue-700 hover:bg-blue-800" onClick={handleAction} data-testid="confirm-action">Confirm</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
